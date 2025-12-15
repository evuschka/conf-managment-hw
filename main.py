import sys
from typing import Any, Dict
from lark import Lark, Transformer, v_args, Token, UnexpectedInput

# ---------------- ГРАММАТИКА ----------------

grammar = r"""
    %import common.WS
    %ignore WS
    %ignore COMMENT

    start: statement*

    ?statement: const_decl | dict_entry

    const_decl: IDENT ":" value ";"           -> declare_const
    dict_entry: IDENT "=" value ","?          -> dict_item

    ?value: number
          | dict
          | const_ref

    dict: "table" "(" "[" dict_entry* "]" ")" -> make_dict

    const_ref: ".(" IDENT ")."                -> use_const

    number: BIN_NUMBER
    BIN_NUMBER: /0[bB][01]+/

    IDENT: /[a-z]+/

    COMMENT: /--\[\[[\s\S]*?\]\]/
"""

# ---------------- ТРАНСФОРМЕР ----------------

class ConfigTransformer(Transformer):
    def __init__(self):
        self.constants: Dict[str, Any] = {}
        self.errors = []

    def IDENT(self, token: Token):
        return token.value

    def number(self, items):
        return int(items[0], 2)

    @v_args(inline=True)
    def declare_const(self, name, value):
        if name in self.constants:
            self.errors.append(f"Constant '{name}' redefined")
        self.constants[name] = value
        return None

    @v_args(inline=True)
    def use_const(self, name):
        if name not in self.constants:
            self.errors.append(f"Undefined constant '{name}'")
            return None
        return self.constants[name]

    @v_args(inline=True)
    def dict_item(self, key, value):
        return key, value

    @v_args(inline=True)
    def make_dict(self, *items):
        result = {}
        for k, v in items:
            if k in result:
                self.errors.append(f"Duplicate key '{k}' in table")
            result[k] = v
        return result

    def start(self, items):
        result = {}
        for item in items:
            if isinstance(item, tuple):
                result[item[0]] = item[1]
        return result

# ---------------- TOML ----------------

def to_toml(data: Dict[str, Any], indent=0) -> str:
    lines = []
    pad = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{pad}[{key}]")
            lines.append(to_toml(value, indent + 1))
        else:
            lines.append(f"{pad}{key} = {value}")

    return "\n".join(lines)

# ---------------- MAIN ----------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <config_file>", file=sys.stderr)
        sys.exit(1)

    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"File error: {e}", file=sys.stderr)
        sys.exit(1)

    parser = Lark(grammar, parser="lalr")
    transformer = ConfigTransformer()

    try:
        tree = parser.parse(text)
        result = transformer.transform(tree)
    except UnexpectedInput as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        sys.exit(1)

    if transformer.errors:
        for err in transformer.errors:
            print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)

    print(to_toml(result))

if __name__ == "__main__":
    main()
