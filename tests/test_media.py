from minuteflow.services.media import MediaService


def test_select_timestamps_respects_limit() -> None:
    service = MediaService()

    timestamps = service._select_timestamps(duration=125.0, interval_seconds=30.0, max_frames=4)

    assert timestamps == [0.0, 30.0, 60.0, 90.0]

