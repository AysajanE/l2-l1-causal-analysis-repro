import argparse


def main():
    parser = argparse.ArgumentParser(description="L2→L1 causal analysis CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("qa", help="Run data QA checks")
    sub.add_parser("panel", help="Build master panel")
    sub.add_parser("models", help="Run models")

    args = parser.parse_args()
    if args.command == "qa":
        print("[CLI] QA checks placeholder → see src/qa/")
    elif args.command == "panel":
        print("[CLI] Panel build placeholder → see sql/ & src/features/")
    elif args.command == "models":
        print("[CLI] Models placeholder → see src/models/")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

