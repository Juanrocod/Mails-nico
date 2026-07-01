def test_change_password(client, auth_headers, test_user, db):
    r = client.post(
        "/auth/change-password",
        json={"old_password": "SecurePass123!", "new_password": "NuevaClave456@"},
        headers=auth_headers,
    )
    assert r.status_code == 204
    db.refresh(test_user)
    from app.core.security import verify_password
    assert verify_password("NuevaClave456@", test_user.hashed_password)


def test_change_password_wrong_old(client, auth_headers):
    r = client.post(
        "/auth/change-password",
        json={"old_password": "wrong", "new_password": "NuevaClave456@"},
        headers=auth_headers,
    )
    assert r.status_code == 401
