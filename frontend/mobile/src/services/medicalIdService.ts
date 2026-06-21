import * as SecureStore from "expo-secure-store";

const MEDICAL_ID_KEY = "medical_id";

export async function saveMedicalId(
  medicalId: unknown
) {
  await SecureStore.setItemAsync(
    MEDICAL_ID_KEY,
    JSON.stringify(medicalId)
  );
}

export async function loadMedicalId() {
  const data =
    await SecureStore.getItemAsync(
      MEDICAL_ID_KEY
    );

  return data ? JSON.parse(data) : null;
}


/**
 * TODO (Option B migration)
 *
 * Replace SecureStore implementation with:
 *
 * GET /api/v1/user/medical-id
 * PUT /api/v1/user/medical-id
 *
 * once backend endpoints are available.
 */