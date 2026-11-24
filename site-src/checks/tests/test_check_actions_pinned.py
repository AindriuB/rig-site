def test_good_passes(run_actions):
    r = run_actions("good")
    assert r.returncode == 0 and r.stdout == ""


def test_major_tag_fails(run_actions):
    r = run_actions("bad_tag")
    assert r.returncode == 1
    assert ".github/workflows/ci.yml:5: actions/checkout@v4: not pinned" in r.stdout


def test_main_and_latest_fail(run_actions):
    r = run_actions("bad_main")
    assert r.returncode == 1
    assert "actions/checkout@main: not pinned" in r.stdout
    assert "actions/x@latest: not pinned" in r.stdout


def test_short_sha_fails(run_actions):
    r = run_actions("bad_sha_short")
    assert r.returncode == 1 and "actions/checkout@0123abc: not pinned" in r.stdout


def test_docker_needs_digest(run_actions):
    r = run_actions("bad_docker")
    assert r.returncode == 1
    assert "docker://alpine:3.20: docker image lacks @sha256: digest" in r.stdout


def test_no_workflows_fails(run_actions):
    r = run_actions("empty")
    assert r.returncode == 1 and "no workflow files found" in r.stdout
