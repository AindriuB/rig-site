def test_good_passes(run_actions):
    r = run_actions("good")
    assert r.returncode == 0 and r.stderr == ""


def test_major_tag_fails(run_actions):
    r = run_actions("bad_tag")
    assert r.returncode == 1
    assert ".github/workflows/ci.yml:4: actions/checkout@v4: not pinned" in r.stderr


def test_main_and_latest_fail(run_actions):
    r = run_actions("bad_main")
    assert r.returncode == 1
    assert "actions/checkout@main: not pinned" in r.stderr
    assert "actions/x@latest: not pinned" in r.stderr


def test_short_sha_fails(run_actions):
    r = run_actions("bad_sha_short")
    assert r.returncode == 1 and "actions/checkout@0123abc: not pinned" in r.stderr


def test_docker_needs_digest(run_actions):
    r = run_actions("bad_docker")
    assert r.returncode == 1
    assert "docker://alpine:3.20: docker image lacks @sha256: digest" in r.stderr


def test_no_workflows_fails(run_actions):
    r = run_actions("empty")
    assert r.returncode == 1 and "no workflow files found" in r.stderr


def test_flow_mapping_step_fails(run_actions):
    r = run_actions("flow_map")
    assert r.returncode == 1 and "actions/checkout@main: not pinned" in r.stderr


def test_yaml_extension_is_checked(run_actions):
    r = run_actions("yaml_ext")
    assert r.returncode == 1 and "deploy.yaml:4: actions/checkout@main: not pinned" in r.stderr


def test_two_uses_on_one_line_all_checked(run_actions):
    r = run_actions("flow_multi")
    assert r.returncode == 1 and "actions/checkout@main: not pinned" in r.stderr


def test_quoted_uses_key_is_checked(run_actions):
    r = run_actions("quoted_key")
    assert r.returncode == 1 and "actions/cache@main: not pinned" in r.stderr


def test_value_on_next_line_fails_closed(run_actions):
    r = run_actions("next_line")
    assert r.returncode == 1 and ".github/workflows/ci.yml:4: uses value not readable" in r.stderr


def test_comment_after_uses_fails_closed(run_actions):
    r = run_actions("comment")
    assert r.returncode == 1 and ".github/workflows/ci.yml:4: uses value not readable" in r.stderr
