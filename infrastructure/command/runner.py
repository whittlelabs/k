import argparse
import json
import os

from infrastructure.di.module_resolution import resolve_module
from infrastructure.di.container import Container
from infrastructure.di.load_definitions import load_definitions_from_yaml
from infrastructure.util.yaml_loader import YamlLoader

# Derive paths from K_PATH if set
K_PATH = os.getenv("K_PATH")
if K_PATH:
    COMMANDS_YAML_PATH = os.path.join(K_PATH, "commands.yaml")
    SERVICES_YAML_PATH = os.path.join(K_PATH, "services.yaml")
else:
    # raise an error
    raise ValueError("K_PATH environment variable must be set")

def build_subcommands(subparsers, commands_dict):
    for cmd_name, cmd_info in commands_dict.items():
        help_text = cmd_info.get("help", "")
        aliases = cmd_info.get("aliases", [])
        subparser = subparsers.add_parser(cmd_name, help=help_text, aliases=aliases)

        if "target" in cmd_info:
            subparser.set_defaults(target=cmd_info["target"])

        # Optional flags
        if "print_result" in cmd_info:
            subparser.set_defaults(print_result=cmd_info["print_result"])
        if "print_map" in cmd_info:
            subparser.set_defaults(print_map=cmd_info["print_map"])

        # Add known arguments (positional or optional)
        for arg_name, arg_value in cmd_info.get("arguments", {}).items():
            if isinstance(arg_value, dict):
                # New logic to support positional arguments with 'nargs'
                if arg_value.get("flag", False):
                    subparser.add_argument(f"--{arg_name}", help=arg_value.get("help", ""), action="store_true", default=False)
                elif arg_value.get("positional", False):
                    subparser.add_argument(arg_name, help=arg_value.get("help", ""), nargs=arg_value.get("nargs", None), default=arg_value.get("default"))
                else:
                    subparser.add_argument(f"--{arg_name}", help=arg_value.get("help", ""), default=arg_value.get("default"), nargs=arg_value.get("nargs", None))
            else:
                # Treat as a required positional argument
                subparser.add_argument(arg_name, help=arg_value)

        # Nested subcommands
        if "subcommands" in cmd_info:
            nested_subparsers = subparser.add_subparsers(dest=f"{cmd_name}_subcommand")
            build_subcommands(nested_subparsers, cmd_info["subcommands"])


def parse_unknown_as_kwargs(unknown_args):
    """
    Convert leftover unknown args of the form:
      --key value
      --key=value
    into a dict: {'key': 'value'}.

    Also treats a flag like --flag with no value as True.
    """
    kwargs = {}
    idx = 0
    while idx < len(unknown_args):
        token = unknown_args[idx]
        # Only process if it starts with --
        if token.startswith("--"):
            if "=" in token:
                # e.g. --foo=bar
                key, value = token.lstrip("-").split("=", 1)
                kwargs[key] = value
            else:
                # e.g. --foo bar or just --foo
                key = token.lstrip("-")
                # Look ahead if there's another arg
                if idx + 1 < len(unknown_args):
                    next_token = unknown_args[idx + 1]
                    if next_token.startswith("--"):
                        # The next token is another flag, so interpret this one as bool
                        kwargs[key] = True
                    else:
                        # next token is a value for this key
                        kwargs[key] = next_token
                        idx += 1
                else:
                    # no next token, treat as True
                    kwargs[key] = True
        else:
            # Some unknown positional leftover. Decide how to handle it (ignore or collect).
            pass
        idx += 1

    return kwargs


def format_result(result, print_map):
    """ Formatting logic (unchanged from your example). """
    fmt = print_map.get("format", "table")
    columns = print_map.get("columns", [])
    order_by = print_map.get("order_by", None)
    print_header = print_map.get("header", "true") == "true"

    if hasattr(result, "data"):
        data = result.data
    elif isinstance(result, list):
        data = result
    else:
        return str(result)

    if order_by:
        def get_key_value(item):
            if isinstance(item, dict):
                return item.get(order_by)
            else:
                return getattr(item, order_by, None)
        data = sorted(data, key=get_key_value)

    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    elif fmt == "table":
        if not columns:
            return str(data)
        lines = []
        header = " | ".join(columns)
        separator = "-" * len(header)
        if print_header:
            lines.append(header)
            lines.append(separator)

        for item in data:
            row_cells = []
            for col in columns:
                # handle dict vs. object
                val = item.get(col) if isinstance(item, dict) else getattr(item, col, None)
                row_cells.append(str(val))
            lines.append(" | ".join(row_cells))
        return "\n".join(lines)

    return str(result)


def load_and_run():
    definitions = load_definitions_from_yaml(SERVICES_YAML_PATH)
    container = Container(definitions)

    yaml_loader = YamlLoader()
    commands_dict = yaml_loader.load_yaml(COMMANDS_YAML_PATH, "commands")
    parser = argparse.ArgumentParser(description="Personal CLI of Keith Morris.")
    subparsers = parser.add_subparsers(dest="top_command")

    build_subcommands(subparsers, commands_dict)

    # 1) parse_known_args to separate recognized vs. leftover
    args, unknown_args = parser.parse_known_args()

    # Generalized nargs handling: for any argument defined with nargs '+' or '*'
    for action in parser._actions:
        if hasattr(action, 'nargs') and action.nargs in ("+", "*"):
            value = getattr(args, action.dest, None)
            if isinstance(value, list) and all(isinstance(v, str) for v in value):
                setattr(args, action.dest, " ".join(value))

    if not args.top_command:
        parser.print_help()
        return

    target = getattr(args, "target", None)
    if not target:
        parser.print_help()
        return

    # 2) Resolve the function from your container
    func = resolve_module(target, container)

    # 3) Build a dictionary from the known argparse results
    args_dict = vars(args).copy()
    print_result = args_dict.pop("print_result", False)
    print_map = args_dict.pop("print_map", None)
    args_dict.pop("target", None)
    args_dict.pop("top_command", None)

    # Remove any subcommand placeholders
    for key in list(args_dict.keys()):
        if key.endswith("_subcommand"):
            args_dict.pop(key)

    # 4) Parse leftover unknown args as **kwargs
    dynamic_kwargs = parse_unknown_as_kwargs(unknown_args)

    # 5) Merge them into the final arg dict
    args_dict.update(dynamic_kwargs)

    # 6) Call the function with known + dynamic arguments
    result = func(**args_dict)

    # 7) Print result if requested
    if print_result:
        if print_map:
            print(format_result(result, print_map))
        else:
            print(result)


if __name__ == "__main__":
    load_and_run()
