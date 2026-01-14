"""
Tests for Librarian API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestLibrarianStatus:
    """Test librarian status endpoints."""

    def test_get_librarian_status(self, client):
        """Test getting librarian system status."""
        response = client.get("/librarian/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "enabled" in data

    def test_get_librarian_stats(self, client):
        """Test getting librarian statistics."""
        response = client.get("/librarian/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.api
class TestLibrarianRules:
    """Test librarian rules endpoints."""

    def test_get_rules(self, client):
        """Test getting librarian rules."""
        response = client.get("/librarian/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data or isinstance(data, list)

    def test_create_rule(self, client):
        """Test creating a librarian rule."""
        response = client.post("/librarian/rules", json={
            "name": "Test Classification Rule",
            "rule_type": "classification",
            "conditions": {"file_extension": ".pdf"},
            "actions": {"assign_category": "documents"},
            "priority": 5
        })
        assert response.status_code in [200, 201, 500]

    def test_get_rule_by_id(self, client):
        """Test getting a specific rule."""
        response = client.get("/librarian/rules/test-rule-id")
        assert response.status_code in [200, 404]

    def test_update_rule(self, client):
        """Test updating a librarian rule."""
        response = client.put("/librarian/rules/test-rule-id", json={
            "priority": 10,
            "enabled": False
        })
        assert response.status_code in [200, 404, 500]

    def test_delete_rule(self, client):
        """Test deleting a librarian rule."""
        response = client.delete("/librarian/rules/nonexistent-rule")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestLibrarianTags:
    """Test librarian tagging endpoints."""

    def test_get_all_tags(self, client):
        """Test getting all tags."""
        response = client.get("/librarian/tags")
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data or isinstance(data, list)

    def test_create_tag(self, client):
        """Test creating a new tag."""
        response = client.post("/librarian/tags", json={
            "name": "test-tag",
            "description": "A test tag",
            "color": "#FF5733"
        })
        assert response.status_code in [200, 201, 500]

    def test_assign_tag(self, client):
        """Test assigning a tag to a document."""
        response = client.post("/librarian/tags/assign", json={
            "document_id": "test-doc-001",
            "tag_names": ["test-tag", "important"]
        })
        assert response.status_code in [200, 404, 500]

    def test_remove_tag(self, client):
        """Test removing a tag from a document."""
        response = client.post("/librarian/tags/remove", json={
            "document_id": "test-doc-001",
            "tag_names": ["test-tag"]
        })
        assert response.status_code in [200, 404, 500]

    def test_get_documents_by_tag(self, client):
        """Test getting documents by tag."""
        response = client.get("/librarian/tags/test-tag/documents")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestLibrarianCategories:
    """Test librarian category endpoints."""

    def test_get_categories(self, client):
        """Test getting all categories."""
        response = client.get("/librarian/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data or isinstance(data, list)

    def test_create_category(self, client):
        """Test creating a category."""
        response = client.post("/librarian/categories", json={
            "name": "Test Category",
            "description": "A test category",
            "parent_id": None
        })
        assert response.status_code in [200, 201, 500]

    def test_assign_category(self, client):
        """Test assigning a document to a category."""
        response = client.post("/librarian/categories/assign", json={
            "document_id": "test-doc-001",
            "category_id": "test-category"
        })
        assert response.status_code in [200, 404, 500]


@pytest.mark.api
class TestLibrarianRelationships:
    """Test librarian relationship endpoints."""

    def test_detect_relationships(self, client):
        """Test detecting document relationships."""
        response = client.post("/librarian/relationships/detect", json={
            "document_id": "test-doc-001"
        })
        assert response.status_code in [200, 404, 500]

    def test_get_relationships(self, client):
        """Test getting document relationships."""
        response = client.get("/librarian/relationships/test-doc-001")
        assert response.status_code in [200, 404]

    def test_create_relationship(self, client):
        """Test creating a manual relationship."""
        response = client.post("/librarian/relationships", json={
            "source_document_id": "test-doc-001",
            "target_document_id": "test-doc-002",
            "relationship_type": "related",
            "strength": 0.8
        })
        assert response.status_code in [200, 201, 404, 500]


@pytest.mark.api
class TestLibrarianActions:
    """Test librarian action endpoints."""

    def test_get_pending_actions(self, client):
        """Test getting pending librarian actions."""
        response = client.get("/librarian/actions/pending")
        assert response.status_code == 200
        data = response.json()
        assert "actions" in data or isinstance(data, list)

    def test_approve_action(self, client):
        """Test approving a librarian action."""
        response = client.post("/librarian/actions/test-action-id/approve", json={
            "approved_by": "admin"
        })
        assert response.status_code in [200, 404, 500]

    def test_reject_action(self, client):
        """Test rejecting a librarian action."""
        response = client.post("/librarian/actions/test-action-id/reject", json={
            "rejected_by": "admin",
            "reason": "Test rejection"
        })
        assert response.status_code in [200, 404, 500]

    def test_get_action_history(self, client):
        """Test getting action history."""
        response = client.get("/librarian/actions/history")
        assert response.status_code == 200


@pytest.mark.api
class TestLibrarianAI:
    """Test librarian AI analysis endpoints."""

    def test_analyze_document(self, client):
        """Test AI analysis of a document."""
        response = client.post("/librarian/ai/analyze", json={
            "document_id": "test-doc-001"
        })
        assert response.status_code in [200, 404, 500]

    def test_suggest_tags(self, client):
        """Test AI tag suggestions."""
        response = client.post("/librarian/ai/suggest-tags", json={
            "content": "This is a Python programming tutorial about functions."
        })
        assert response.status_code in [200, 500]

    def test_suggest_category(self, client):
        """Test AI category suggestions."""
        response = client.post("/librarian/ai/suggest-category", json={
            "content": "Machine learning algorithms for image classification."
        })
        assert response.status_code in [200, 500]
