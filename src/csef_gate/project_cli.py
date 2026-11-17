from pathlib import Path
from .core import read_json, Refused
from .project import ProjectBook


def configure(sub):
    parser = sub.add_parser("project", help="persistent goals, questions and staged handoff packets")
    commands = parser.add_subparsers(dest="project_command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--root", type=Path, required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--brief", type=Path, help="optional owner answers and stable facts JSON")
    for name in ("status", "questions", "packet", "answer", "review", "assist", "route"):
        p = commands.add_parser(name)
        p.add_argument("--root", type=Path, required=True)
        if name == "packet":
            p.add_argument("--stage", required=True)
            p.add_argument("--inline", action="store_true")
        if name in ("review", "assist"):
            p.add_argument("--stage", required=True)
            p.add_argument("--provider", choices=("openai", "anthropic", "codex"))
            p.add_argument("--model", help="required for direct APIs")
        if name == "review":
            p.add_argument("--proposal", type=Path, required=True)
        if name == "route":
            p.add_argument("--stage", required=True)
            p.add_argument("--signal", action="append", default=[])
            p.add_argument("--always", action="store_true")
        if name == "answer":
            p.add_argument("--id", required=True)
            p.add_argument("--text", required=True)
            p.add_argument("--version", type=int)
            p.add_argument("--fact", nargs=2, action="append", default=[], metavar=("ID", "TEXT"))
    return parser


def execute(args):
    if args.project_command == "init":
        brief = read_json(args.brief) if args.brief else {}
        if set(brief) - {"answers", "facts", "stages"}:
            raise Refused("brief supports answers, facts and optional stage definitions")
        return ProjectBook.create(args.root, args.goal, **brief).status()
    book = ProjectBook(args.root)
    if args.project_command == "status":
        return book.status()
    if args.project_command == "questions":
        return {"questions": book.questions()}
    if args.project_command == "packet":
        return book.context(args.stage) if args.inline else book.packet(args.stage)
    if args.project_command in ("review", "assist"):
        from .providers.direct import select_provider
        client, _ = select_provider(args.provider, args.model)
        if args.project_command == "review":
            from .review import review_proposal
            return review_proposal(book, args.stage, read_json(args.proposal), client)
        from .assistant import assist_stage
        return assist_stage(book, args.stage, client)
    if args.project_command == "route":
        from .review import route_review
        book.packet(args.stage)
        return route_review(args.stage, args.signal, always=args.always)
    from .lifecycle.questions import Questions
    updates = dict(args.fact)
    if len(updates) != len(args.fact):
        raise Refused("duplicate fact update")
    Questions(book).answer(args.id, args.text, expected_version=args.version if args.version is not None else book.current()["version"], fact_updates=updates)
    return book.status()
