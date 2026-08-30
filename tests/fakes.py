"""Synthetic API payloads. No real tokens, VIN, IMEI, or phones."""

FAKE_ACCESS = "test-access-token"
FAKE_REFRESH = "test-refresh-token"
FAKE_ACCESS_2 = "test-access-token-rotated"
FAKE_REFRESH_2 = "test-refresh-token-rotated"
FAKE_USER_ID = "user-test-0001"
FAKE_CAR_ID = "aaaaaaaaaaaaaaaaaaaaaaaa"
FAKE_IMEI = "000000000000000"
FAKE_VIN = "TESTVIN0000000001"
FAKE_PLATE = "TEST-000"
FAKE_PHONE = "0000000000"


def vehicle_row() -> dict:
    return {
        "_id": FAKE_CAR_ID,
        "imei": FAKE_IMEI,
        "vin": FAKE_VIN,
        "licensePlate": FAKE_PLATE,
        "brand": "Evolute",
        "carModel": {"name": "i-PRO", "options": {"heater": True}},
    }


def telemetry_payload() -> dict:
    return {
        "isOnline": True,
        "onlineState": "online",
        "isCarStateReady": True,
        "carStateUpdatedAt": 1_700_000_000_000,
        "sensors": {
            "batteryPercentage": "64",
            "remainsBatteryMileage": "212",
            "batteryTemp": "21.5",
            "12VBatteryVoltage": "12.6",
            "isChargingGunInserted": "false",
            "climateTargetTemp": "22",
            "climateFanSpeed": "2",
            "inBoardTemp": "19",
            "outsideTemp": "8",
            "coolantTemp": "30",
            "isCentralLockingOn": "true",
            "doorFLStatus": "0",
            "doorFRStatus": "0",
            "doorRLStatus": "0",
            "doorRRStatus": "0",
            "trunkStatus": "0",
            "headLightsStatus": "0",
            "isIgnitionOn": "false",
            "isParkedOn": "true",
            "odometer": "12345",
            "signalLevel": "4",
            "lat": "55.000000",
            "lon": "37.000000",
            "course": "90",
        },
        "buttons": [
            {
                "title": "Climate",
                "status": "off",
                "enabled": True,
                "activateCommand": "climateOn",
                "deactivateCommand": "climateOff",
            }
        ],
        "warnings": [],
    }


def trip_row() -> dict:
    return {
        "id": 101,
        "segmentStartTime": 1_700_000_100,
        "segmentEndTime": 1_700_001_000,
        "startDate": 1_700_000_100,
        "endDate": 1_700_001_000,
        "title": "Home → Work",
        "description": "redacted-address-placeholder",
        "duration": "00:15:00",
        "distance": 8500,
        "batteryConsumption": 6,
        "odometer": {"first": 1000, "last": 1008},
        "battery": {"first": 80, "last": 74},
        "fuel": {"first": None, "last": None},
    }
