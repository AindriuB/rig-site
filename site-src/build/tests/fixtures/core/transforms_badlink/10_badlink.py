def apply(ctx):
    (ctx.docs_dir / "broken.md").write_text("# Broken\n\nSee [nowhere](nowhere.md).\n")
