def apply(ctx):
    (ctx.docs_dir / "assets").mkdir(exist_ok=True)
    (ctx.docs_dir / "assets" / "mark.txt").write_text(ctx.id)
    index = ctx.docs_dir / "index.md"
    index.write_text(index.read_text() + "\nTransformed.\n")
