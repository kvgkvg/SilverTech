from __future__ import annotations


def test_panasonic_demo_guidance_questions(client):
    cases = ["Làm sao để nướng thịt?", "Tôi muốn rã đông thịt thì cần làm gì?", "Làm sao để hẹn giờ 30 phút?"]
    valid_button_ids = {
        "micro_power",
        "time_10_min",
        "grill",
        "time_1_min",
        "combination",
        "time_10_sec",
        "turbo_defrost",
        "up",
        "auto_reheat",
        "down",
        "auto_menu",
        "time_clock",
        "add_time",
        "quick_30",
        "stop_reset",
        "start",
    }

    for query in cases:
        response = client.post(
            "/api/query",
            json={
                "template_id": "template_panasonic_microwave_nn_gt35hm_v1",
                "user_query_text": query,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["intent"]
        assert body["steps"]
        assert all(step["button_id"] in valid_button_ids for step in body["steps"])
