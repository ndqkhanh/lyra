"""Tests for multi_tenant bridge — TenantContext, TenantVault, TenantBridge."""

import os
import tempfile

from lyra_core.multi_tenant import (
    TenantBridge,
    TenantContext,
    TenantMetadata,
    TenantTier,
    TenantVault,
)


class TestTenantTier:
    def test_all_tiers(self):
        assert TenantTier.FREE == "free"
        assert TenantTier.PRO == "pro"
        assert TenantTier.ENTERPRISE == "enterprise"
        assert TenantTier.INTERNAL == "internal"


class TestTenantMetadata:
    def test_empty_metadata(self):
        md = TenantMetadata()
        assert md.to_dict() == {}

    def test_set_and_get(self):
        md = TenantMetadata()
        md.set("com.acme.department", "engineering")
        assert md.get("com.acme.department") == "engineering"

    def test_get_default(self):
        md = TenantMetadata()
        assert md.get("nonexistent", "default") == "default"

    def test_delete_existing(self):
        md = TenantMetadata()
        md.set("key", "val")
        assert md.delete("key") is True
        assert md.get("key") == ""

    def test_delete_nonexistent(self):
        md = TenantMetadata()
        assert md.delete("nope") is False

    def test_prefixed_filter(self):
        md = TenantMetadata()
        md.set("com.acme.dept", "eng")
        md.set("com.acme.region", "us-east")
        md.set("org.other.key", "val")
        prefixed = md.prefixed("com.acme.")
        assert len(prefixed) == 2
        assert "com.acme.dept" in prefixed
        assert "com.acme.region" in prefixed
        assert "org.other.key" not in prefixed

    def test_to_dict_returns_copy(self):
        md = TenantMetadata()
        md.set("a", "1")
        d = md.to_dict()
        d["b"] = "2"
        assert "b" not in md.data

    def test_init_with_data(self):
        md = TenantMetadata(data={"k": "v"})
        assert md.get("k") == "v"


class TestTenantContext:
    def test_create_with_id(self):
        ctx = TenantContext.create("acme-corp")
        assert ctx.tenant_id == "acme-corp"
        assert ctx.tier == TenantTier.FREE

    def test_create_generates_id(self):
        ctx = TenantContext.create()
        assert ctx.tenant_id.startswith("tenant_")
        assert len(ctx.tenant_id) > 8

    def test_create_with_tier(self):
        ctx = TenantContext.create("acme-corp", tier=TenantTier.ENTERPRISE)
        assert ctx.tier == TenantTier.ENTERPRISE

    def test_create_with_metadata(self):
        ctx = TenantContext.create("acme-corp", metadata={"dept": "eng"})
        assert ctx.metadata.get("dept") == "eng"

    def test_is_internal(self):
        ctx = TenantContext.create("sys", tier=TenantTier.INTERNAL)
        assert ctx.is_internal is True
        assert ctx.is_enterprise is True

    def test_is_enterprise(self):
        ctx = TenantContext.create("acme", tier=TenantTier.ENTERPRISE)
        assert ctx.is_internal is False
        assert ctx.is_enterprise is True

    def test_free_is_not_enterprise(self):
        ctx = TenantContext.create("free-user")
        assert ctx.is_enterprise is False

    def test_tag_and_has_tag(self):
        ctx = TenantContext.create("acme")
        ctx.tag("dept", "eng")
        assert ctx.has_tag("dept") is True
        assert ctx.has_tag("nonexistent") is False

    def test_summary(self):
        ctx = TenantContext.create("acme", tier=TenantTier.PRO,
                                   metadata={"dept": "eng"})
        s = ctx.summary()
        assert s["tenant_id"] == "acme"
        assert s["tier"] == "pro"
        assert "dept" in s["metadata_keys"]

    def test_tenant_id_persisted(self):
        ctx = TenantContext.create("original")
        assert ctx.tenant_id == "original"


class TestTenantVault:
    def test_vault_creates_tenant_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("acme-corp", base_dir=tmp)
            vault.ensure_dir()
            assert os.path.isdir(vault.tenant_dir)

    def test_tenant_dir_path(self):
        vault = TenantVault("acme-corp", base_dir="/tmp/lyra-test")
        assert vault.tenant_dir == "/tmp/lyra-test/acme-corp"

    def test_auth_path(self):
        vault = TenantVault("acme-corp", base_dir="/tmp/lyra-test")
        assert vault.auth_path == "/tmp/lyra-test/acme-corp/auth.json"

    def test_metadata_path(self):
        vault = TenantVault("acme-corp", base_dir="/tmp/lyra-test")
        assert vault.metadata_path == "/tmp/lyra-test/acme-corp/metadata.json"

    def test_exists_after_ensure(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("acme-corp", base_dir=tmp)
            assert vault.exists() is False
            vault.ensure_dir()
            assert vault.exists() is True

    def test_delete_removes_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("acme-corp", base_dir=tmp)
            vault.ensure_dir()
            assert vault.delete() is True
            assert vault.exists() is False

    def test_delete_nonexistent_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("acme-corp", base_dir=tmp)
            assert vault.delete() is False

    def test_list_tenants(self):
        with tempfile.TemporaryDirectory() as tmp:
            TenantVault("tenant-a", base_dir=tmp).ensure_dir()
            TenantVault("tenant-b", base_dir=tmp).ensure_dir()
            vault = TenantVault("tenant-a", base_dir=tmp)
            tenants = vault.list_tenants()
            assert "tenant-a" in tenants
            assert "tenant-b" in tenants

    def test_list_tenants_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("any", base_dir=tmp)
            assert vault.list_tenants() == []

    def test_ensure_dir_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = TenantVault("acme-corp", base_dir=tmp)
            vault.ensure_dir()
            vault.ensure_dir()  # Should not raise
            assert vault.exists() is True


class TestTenantBridge:
    def test_register_new_tenant(self):
        bridge = TenantBridge()
        ctx = bridge.register("acme-corp", tier=TenantTier.ENTERPRISE)
        assert ctx.tenant_id == "acme-corp"
        assert ctx.tier == TenantTier.ENTERPRISE
        assert bridge.count() == 1

    def test_register_duplicate_returns_existing(self):
        bridge = TenantBridge()
        ctx1 = bridge.register("acme-corp")
        ctx2 = bridge.register("acme-corp")
        assert ctx1 is ctx2

    def test_register_with_metadata(self):
        bridge = TenantBridge()
        ctx = bridge.register("acme-corp", metadata={"dept": "eng"})
        assert ctx.metadata.get("dept") == "eng"

    def test_resolve_existing(self):
        bridge = TenantBridge()
        bridge.register("acme-corp")
        ctx = bridge.resolve("acme-corp")
        assert ctx is not None
        assert ctx.tenant_id == "acme-corp"

    def test_resolve_nonexistent(self):
        bridge = TenantBridge()
        assert bridge.resolve("ghost") is None

    def test_remove_existing(self):
        bridge = TenantBridge()
        bridge.register("acme-corp")
        assert bridge.remove("acme-corp") is True
        assert bridge.count() == 0
        assert bridge.resolve("acme-corp") is None

    def test_remove_nonexistent(self):
        bridge = TenantBridge()
        assert bridge.remove("ghost") is False

    def test_tag_tenant(self):
        bridge = TenantBridge()
        ctx = bridge.register("acme-corp")
        bridge.tag(ctx, "com.acme.dept", "engineering")
        assert ctx.has_tag("com.acme.dept") is True
        assert ctx.metadata.get("com.acme.dept") == "engineering"

    def test_find_by_tag(self):
        bridge = TenantBridge()
        ctx1 = bridge.register("acme-corp")
        ctx2 = bridge.register("other-corp")
        bridge.tag(ctx1, "region", "us-east")
        bridge.tag(ctx2, "region", "eu-west")
        found = bridge.find_by_tag("region", "us-east")
        assert len(found) == 1
        assert found[0].tenant_id == "acme-corp"

    def test_find_by_tag_no_match(self):
        bridge = TenantBridge()
        bridge.register("acme-corp")
        assert bridge.find_by_tag("nonexistent", "val") == []

    def test_find_by_tier(self):
        bridge = TenantBridge()
        bridge.register("free-1", tier=TenantTier.FREE)
        bridge.register("pro-1", tier=TenantTier.PRO)
        bridge.register("free-2", tier=TenantTier.FREE)
        free_tenants = bridge.find_by_tier(TenantTier.FREE)
        assert len(free_tenants) == 2

    def test_find_by_tier_empty(self):
        bridge = TenantBridge()
        bridge.register("free-1", tier=TenantTier.FREE)
        assert bridge.find_by_tier(TenantTier.ENTERPRISE) == []

    def test_list_ids(self):
        bridge = TenantBridge()
        bridge.register("tenant-c")
        bridge.register("tenant-a")
        bridge.register("tenant-b")
        assert bridge.list_ids() == ["tenant-a", "tenant-b", "tenant-c"]

    def test_summary(self):
        bridge = TenantBridge()
        bridge.register("free-1", tier=TenantTier.FREE)
        bridge.register("pro-1", tier=TenantTier.PRO)
        s = bridge.summary()
        assert s["total_tenants"] == 2
        assert s["by_tier"]["free"] == 1
        assert s["by_tier"]["pro"] == 1

    def test_multiple_tenants_independent_metadata(self):
        bridge = TenantBridge()
        ctx1 = bridge.register("tenant-1")
        ctx2 = bridge.register("tenant-2")
        bridge.tag(ctx1, "key", "val1")
        bridge.tag(ctx2, "key", "val2")
        assert ctx1.metadata.get("key") == "val1"
        assert ctx2.metadata.get("key") == "val2"
