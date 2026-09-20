"""
Deployment configuration: what production actually runs.

These assert configuration rather than behaviour, because the failure they
guard against has no other visible symptom. `docker-compose.prod.yml` used to
override only `restart:` for the frontend, so production silently inherited
`command: npm run dev` from the base file and served the SPA from the Vite dev
server — unminified, over HMR, and needing 'unsafe-inline'/'unsafe-eval' in the
CSP because HMR requires them. Nothing was broken; it just quietly was not what
anyone thought it was.

Parsed as plain YAML rather than shelling out to `docker compose config`, so
these run anywhere pytest does, with no Docker daemon and no environment.
"""

import pathlib

import pytest

yaml = pytest.importorskip('yaml')

REPO = pathlib.Path(__file__).resolve().parents[3]
BASE = REPO / 'docker-compose.yml'
PROD = REPO / 'docker-compose.prod.yml'
OVERRIDE = REPO / 'docker-compose.override.yml'
NGINX_TEMPLATE = REPO / 'compose' / 'nginx-frontend.conf.template'
DOCKERIGNORE = REPO / '.dockerignore'

FRONTEND = 'frontend-vetimage'

# Only `app/backend` is mounted into the backend container, so these files are
# out of reach when the suite runs there. CI checks the whole repo out and runs
# pytest from `app/backend` on the runner, which is where these do their work;
# locally, run them from the repo root with `python -m pytest app/backend/tests/
# test_deployment_config.py`.
pytestmark = pytest.mark.skipif(
    not BASE.exists(),
    reason='compose files not reachable from here (run from a full checkout)',
)


def _services(path):
    return yaml.safe_load(path.read_text())['services']


@pytest.fixture(scope='module')
def base():
    return _services(BASE)[FRONTEND]


@pytest.fixture(scope='module')
def prod():
    return _services(PROD)[FRONTEND]


class TestProductionServesABuiltBundle:

    def test_it_builds_the_serve_target(self, prod):
        assert prod['build']['target'] == 'serve'

    def test_it_does_not_inherit_the_dev_server(self, prod):
        """
        The bug this file exists for. Compose merges keys, so an override that
        does not mention `command` keeps the base file's — and the base runs
        `npm run dev`.
        """
        assert prod.get('command') == [], (
            'production must clear the base command, or it runs the Vite dev server'
        )

    def test_both_files_name_their_target_explicitly(self, base, prod):
        """
        Otherwise the target is whichever stage happens to be last in the
        Dockerfile, and re-ordering that file changes what production runs.
        """
        assert base['build']['target'] == 'dev'
        assert prod['build']['target'] == 'serve'

    def test_the_build_refuses_to_run_without_its_origins(self, prod):
        """
        Vite inlines `import.meta.env.*` at build time, so an image built
        without these is silently wired to localhost. `:?` fails the build
        rather than shipping that.
        """
        args = prod['build']['args']
        for key in ('VITE_API_URL', 'VITE_WS_URL'):
            assert key in args
            assert ':?' in args[key], f'{key} must be required, not defaulted'

    def test_the_healthcheck_suits_the_image_it_runs_in(self, prod):
        """
        The base healthcheck uses curl, which the node image has and
        nginx:alpine does not — inherited unchanged it marks a healthy
        container unhealthy for ever.
        """
        test = prod['healthcheck']['test']
        assert 'curl' not in ' '.join(test)


class TestTheSourceTreeStaysOutOfProduction:

    def test_the_base_file_does_not_mount_the_frontend_source(self, base):
        """
        Compose *merges* volume lists and cannot remove an entry an earlier
        file added, so a source mount in the base file follows the built bundle
        into the production image. Dev-only mounts belong in the override.
        """
        sources = [v.split(':')[0] for v in base.get('volumes', [])]
        assert './app/frontend/' not in sources
        assert not any(s.startswith('./app/frontend') for s in sources)

    def test_the_override_still_provides_it_for_development(self):
        volumes = _services(OVERRIDE)[FRONTEND]['volumes']
        assert any(v.startswith('./app/frontend') for v in volumes), (
            'hot reload needs the source mount'
        )

    def test_the_dangling_static_symlink_is_excluded_from_the_build(self):
        """
        `app/frontend/public/static` is a committed symlink to an absolute path
        that only resolves inside a container with shared_volume mounted. Vite
        copies public/ wholesale, so in a clean image it stats a dangling link
        and the build dies with ENOENT — which is why the production bundle had
        never been built outside a running dev container.
        """
        assert 'app/frontend/public/static' in DOCKERIGNORE.read_text()


class TestTheProductionPolicyIsTheStrictOne:
    """
    The reason for building the bundle at all. The dev server's policy has to
    allow 'unsafe-inline' and 'unsafe-eval' for HMR; a built bundle loads its
    code from external module scripts and needs neither.
    """

    @pytest.fixture(scope='class')
    def policy(self):
        text = NGINX_TEMPLATE.read_text()
        line = next(
            ln for ln in text.splitlines()
            if 'add_header Content-Security-Policy' in ln
        )
        return line

    def test_script_src_allows_nothing_but_self(self, policy):
        script_src = policy.split('script-src ')[1].split(';')[0]
        assert script_src.strip() == "'self'"

    def test_no_unsafe_eval_anywhere(self, policy):
        assert 'unsafe-eval' not in policy

    def test_style_src_keeps_unsafe_inline_deliberately(self, policy):
        """
        React writes `style={{…}}` as an inline style attribute, which
        style-src governs. Removing this would mean removing every inline style
        in the app for far less benefit than the script-src tightening.
        """
        style_src = policy.split('style-src ')[1].split(';')[0]
        assert "'unsafe-inline'" in style_src

    def test_violations_are_reported(self, policy):
        """Enforced without reporting means a blocked resource fails silently."""
        assert '${CSP_REPORT_URI}' in policy

    def test_connect_src_is_configurable(self, policy):
        """
        The SPA calls the backend cross-origin. A hard-coded 'self' would put
        every API call and WebSocket in violation, and with the policy enforced
        that takes the whole app down.
        """
        assert '${CSP_CONNECT_SRC}' in policy


class TestTheNginxConfigDoesNotDropHeaders:

    def test_security_headers_are_not_declared_inside_a_location(self):
        """
        `add_header` in a location block discards every header inherited from
        the server block. A per-location Cache-Control would silently strip the
        CSP from index.html — the one document where it matters most — which is
        why Cache-Control is chosen by a mapped variable instead.
        """
        text = NGINX_TEMPLATE.read_text()
        inside_location = False
        depth = 0
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('location '):
                inside_location = True
                depth = 0
            if inside_location:
                depth += line.count('{') - line.count('}')
                assert not stripped.startswith('add_header'), (
                    f'add_header inside a location block drops inherited '
                    f'headers: {stripped}'
                )
                if depth <= 0 and '}' in line:
                    inside_location = False
