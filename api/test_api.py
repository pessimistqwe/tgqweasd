"""
EventPredict API Tests
Tests for backend functionality
"""
import pytest
import requests
import json

BASE_URL = "https://eventpredict-production.up.railway.app"

class TestHealth:
    """Test health endpoint"""
    
    def test_health_check(self):
        """Test that health endpoint returns healthy status"""
        response = requests.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "sync" in data
        assert data["sync"]["total_synced"] > 0


class TestCategories:
    """Test categories endpoint"""
    
    def test_get_categories(self):
        """Test that categories endpoint returns all categories"""
        response = requests.get(f"{BASE_URL}/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) >= 7  # all, politics, sports, crypto, etc.


class TestEvents:
    """Test events endpoints"""
    
    def test_get_events(self):
        """Test that events endpoint returns events"""
        response = requests.get(f"{BASE_URL}/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert len(data["events"]) > 0
    
    def test_get_events_crypto_category(self):
        """Test that crypto category returns crypto events"""
        response = requests.get(f"{BASE_URL}/events?category=crypto")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        # All events should be crypto category
        for event in data["events"]:
            assert event["category"] == "crypto"
    
    def test_get_events_sports_category(self):
        """Test that sports category returns sports events"""
        response = requests.get(f"{BASE_URL}/events?category=sports")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        # All events should be sports category
        for event in data["events"]:
            assert event["category"] == "sports"
    
    def test_get_single_event(self):
        """Test that single event endpoint returns event details"""
        # First get events list
        events_response = requests.get(f"{BASE_URL}/events")
        events = events_response.json()["events"]
        if events:
            event_id = events[0]["id"]
            response = requests.get(f"{BASE_URL}/events/{event_id}")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "title" in data
            assert "options" in data


class TestAdmin:
    """Test admin endpoints"""
    
    ADMIN_ID = 1972885597
    
    def test_admin_check(self):
        """Test admin check endpoint"""
        response = requests.get(f"{BASE_URL}/admin/check/{self.ADMIN_ID}")
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] == True
    
    def test_admin_check_non_admin(self):
        """Test admin check for non-admin user"""
        response = requests.get(f"{BASE_URL}/admin/check/123456")
        assert response.status_code == 200
        data = response.json()
        assert "is_admin" in data
        assert data["is_admin"] == False
    
    def test_admin_stats(self):
        """Test admin stats endpoint"""
        response = requests.get(f"{BASE_URL}/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data or "total_events" in data
    
    def test_price_history_endpoint(self):
        """Test price history endpoint exists"""
        # Get first event
        events_response = requests.get(f"{BASE_URL}/events")
        events = events_response.json()["events"]
        if events:
            event_id = events[0]["id"]
            response = requests.get(f"{BASE_URL}/events/{event_id}/price-history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestUser:
    """Test user endpoints"""
    
    def test_get_user(self):
        """Test getting user info"""
        response = requests.get(f"{BASE_URL}/user/123456")
        assert response.status_code == 200
        data = response.json()
        assert "telegram_id" in data
        assert "points" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
