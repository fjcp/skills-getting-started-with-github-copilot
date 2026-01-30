"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    # Store original state
    original_activities = {
        k: {"participants": v["participants"].copy(), **{kk: vv for kk, vv in v.items() if kk != "participants"}}
        for k, v in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for activity_name, activity_data in activities.items():
        activity_data["participants"] = original_activities[activity_name]["participants"].copy()


class TestGetActivities:
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_get_activities_contains_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data


class TestSignup:
    def test_signup_for_activity_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert email in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]

    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post("/activities/Nonexistent Club/signup?email=test@example.com")
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that duplicate signup is prevented"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_url_encoding(self, client, reset_activities):
        """Test signup with URL-encoded email"""
        email = "test+special@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200


class TestUnregister:
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        assert email in response.json()["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]

    def test_unregister_invalid_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.post("/activities/Nonexistent Club/unregister?email=test@example.com")
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_signed_up(self, client, reset_activities):
        """Test unregister for student not in activity"""
        email = "notregistered@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]


class TestParticipantManagement:
    def test_signup_and_unregister_flow(self, client, reset_activities):
        """Test complete signup and unregister flow"""
        email = "testuser@mergington.edu"
        activity = "Programming Class"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregister
        activities_response = client.get("/activities")
        assert email not in activities_response.json()[activity]["participants"]

    def test_multiple_participants_handling(self, client, reset_activities):
        """Test handling of multiple participants in an activity"""
        activity = "Drama Club"
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        
        email = "newdramauser@mergington.edu"
        client.post(f"/activities/{activity}/signup?email={email}")
        
        updated_response = client.get("/activities")
        updated_count = len(updated_response.json()[activity]["participants"])
        
        assert updated_count == initial_count + 1
