from __future__ import annotations


def test_panasonic_demo_guidance_questions(client):
    cases = [
        ("Làm sao để nướng thịt?", "grill_meat", ["grill", "time_10_min", "start"]),
        (
            "Tôi muốn rã đông thịt thì cần làm gì?",
            "defrost_meat",
            ["turbo_defrost", "up", "start"],
        ),
        (
            "Làm sao để hẹn giờ 30 phút?",
            "set_timer_30_minutes",
            ["time_clock", "time_10_min", "start"],
        ),
    ]

    for query, intent, button_ids in cases:
        response = client.post(
            "/api/query",
            json={
                "template_id": "template_panasonic_microwave_nn_gt35hm_v1",
                "user_query_text": query,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["intent"] == intent
        assert [step["button_id"] for step in body["steps"]] == button_ids
