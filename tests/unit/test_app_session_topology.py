"""Unit tests for hullq.api.app's SLICE-0053 session-topology invariant.

Independent review (2026-09-14, exact-head 9777496): the HullQ session
cookie is host-only, so the browser-visible FastAPI auth/callback endpoint
and the Astro Broker Workspace surface must share the same hostname. A
mismatched configuration (e.g. `api.hullq.com` for auth/callback vs
`hullq.com` for `/broker`) must fail closed rather than silently produce a
successful login followed by an unauthenticated workspace.
"""

from __future__ import annotations

import pytest

from hullq.api.app import SessionTopologyError, require_same_host_session_topology


class TestRequireSameHostSessionTopology:
    def test_none_web_base_url_always_passes(self) -> None:
        # A relative post-login redirect always resolves against the
        # auth/callback's own origin: inherently same-host.
        require_same_host_session_topology(
            redirect_uri="https://hullq.example/api/auth/callback", web_base_url=None
        )

    def test_identical_host_passes(self) -> None:
        require_same_host_session_topology(
            redirect_uri="https://hullq.example/api/auth/callback",
            web_base_url="https://hullq.example/",
        )

    def test_identical_host_different_ports_passes(self) -> None:
        # Local dev / the retained proof: same hostname, different ports.
        require_same_host_session_topology(
            redirect_uri="http://127.0.0.1:8001/api/auth/callback",
            web_base_url="http://127.0.0.1:8002",
        )

    def test_same_host_reverse_proxy_different_paths_passes(self) -> None:
        require_same_host_session_topology(
            redirect_uri="https://hullq.example/api/auth/callback",
            web_base_url="https://hullq.example/app",
        )

    def test_different_hostnames_rejected(self) -> None:
        with pytest.raises(SessionTopologyError, match=r"api\.hullq\.example"):
            require_same_host_session_topology(
                redirect_uri="https://api.hullq.example/api/auth/callback",
                web_base_url="https://hullq.example/",
            )

    def test_subdomain_vs_apex_rejected(self) -> None:
        # A subdomain and its apex domain are different hosts for
        # host-only-cookie purposes -- never treated as "close enough".
        with pytest.raises(SessionTopologyError):
            require_same_host_session_topology(
                redirect_uri="https://auth.hullq.example/api/auth/callback",
                web_base_url="https://hullq.example/",
            )

    def test_case_insensitive_host_comparison(self) -> None:
        # Hostnames are case-insensitive; urlsplit().hostname already
        # lowercases, so this must not be flagged as a mismatch.
        require_same_host_session_topology(
            redirect_uri="https://Hullq.Example/api/auth/callback",
            web_base_url="https://hullq.example/",
        )
