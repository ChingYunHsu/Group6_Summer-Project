import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";
import {
  AllergyKey,
  allergies as allergyList,
  getAllergyLabel,
} from "../data/allergies";
import {
  MedicalConditionKey,
  medicalConditions,
  getConditionLabel,
} from "../data/medicalConditions";
import i18n from "../i18n";
import type { MedicalProfile } from "../services/medicalIdService";
import {
  DEFAULT_MEDICAL_PROFILE,
  loadMedicalId,
  saveMedicalId,
} from "../services/medicalIdService";
import { loadProfile } from "../services/profileService";

const BLOOD_TYPES = [
  "A+",
  "A-",
  "B+",
  "B-",
  "AB+",
  "AB-",
  "O+",
  "O-",
  "Unknown",
];

type SupportedLangCode = "en" | "es" | "fr" | "it" | "de" | "zh";

const SUPPORTED_LANG_CODES: SupportedLangCode[] = [
  "en",
  "es",
  "fr",
  "it",
  "de",
  "zh",
];

export default function MedicalIdScreen() {
  const { t } = useTranslation();

  const currentLangCode: SupportedLangCode = SUPPORTED_LANG_CODES.includes(
    i18n.language as SupportedLangCode,
  )
    ? (i18n.language as SupportedLangCode)
    : "en";

  const [conditionModalVisible, setConditionModalVisible] = useState(false);

  const [allergyModalVisible, setAllergyModalVisible] = useState(false);

  const [bloodTypeModalVisible, setBloodTypeModalVisible] = useState(false);

  const [newCondition, setNewCondition] = useState("");

  const [newAllergy, setNewAllergy] = useState("");

  const [medicalId, setMedicalId] = useState<MedicalProfile>(
    DEFAULT_MEDICAL_PROFILE,
  );

  const [fullName, setFullName] = useState("");

  const [bloodType, setBloodType] = useState(medicalId.blood_type);

  const [conditions, setConditions] = useState(medicalId.conditions);

  const [saving, setSaving] = useState(false);

  const [allergies, setAllergies] = useState(medicalId.allergies ?? []);

  // Suggestions from the curated lists, filtered by the current input
  // text and matched against the current app language's labels. Stored
  // items (conditions/allergies) that already match a suggestion — by
  // key or by translated label — are excluded so the same term can't be
  // added twice under two different representations.
  const conditionSuggestions = useMemo(() => {
    const query = newCondition.trim().toLowerCase();
    if (!query) return [];

    return (Object.keys(medicalConditions) as MedicalConditionKey[])
      .filter((key) =>
        medicalConditions[key][currentLangCode].toLowerCase().includes(query),
      )
      .filter(
        (key) =>
          !conditions.some(
            (item) =>
              item.toLowerCase() === key.toLowerCase() ||
              item.toLowerCase() ===
                medicalConditions[key][currentLangCode].toLowerCase(),
          ),
      )
      .slice(0, 6);
  }, [newCondition, conditions, currentLangCode]);

  const allergySuggestions = useMemo(() => {
    const query = newAllergy.trim().toLowerCase();
    if (!query) return [];

    return (Object.keys(allergyList) as AllergyKey[])
      .filter((key) =>
        allergyList[key][currentLangCode].toLowerCase().includes(query),
      )
      .filter(
        (key) =>
          !allergies.some(
            (item) =>
              item.toLowerCase() === key.toLowerCase() ||
              item.toLowerCase() ===
                allergyList[key][currentLangCode].toLowerCase(),
          ),
      )
      .slice(0, 6);
  }, [newAllergy, allergies, currentLangCode]);

  const handleSave = async () => {
    try {
      setSaving(true);

      const updatedMedicalId = {
        date_of_birth: medicalId.date_of_birth,
        gender: medicalId.gender,
        address: medicalId.address,
        blood_type: bloodType,
        allergies,
        conditions,
        medications: medicalId.medications,
        emergency_contacts: medicalId.emergency_contacts,
      };

      const savedProfile = await saveMedicalId(updatedMedicalId);

      setMedicalId(savedProfile);

      router.back();
    } catch (error) {
      console.error("Failed to save medical ID", error);
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    async function getMedicalId() {
      try {
        const savedMedicalId = await loadMedicalId();

        if (savedMedicalId) {
          setMedicalId(savedMedicalId);

          setBloodType(savedMedicalId.blood_type);
          setConditions(savedMedicalId.conditions);
          setAllergies(savedMedicalId.allergies ?? []);
        }

        const profile = await loadProfile();

        setFullName(profile.full_name);
      } catch (error) {
        console.error("Failed to load medical ID", error);
      }
    }

    getMedicalId();
  }, []);

  const removeCondition = (condition: string) => {
    setConditions(conditions.filter((item) => item !== condition));
  };

  const removeAllergy = (allergy: string) => {
    setAllergies(allergies.filter((item) => item !== allergy));
  };

  // Stores the curated key (e.g. "asthma"), not the translated label —
  // this is what lets the same entry render correctly in whatever
  // language the app is later switched to.
  const selectConditionSuggestion = (key: MedicalConditionKey) => {
    setConditions([...conditions, key]);
    setNewCondition("");
    setConditionModalVisible(false);
  };

  const selectAllergySuggestion = (key: AllergyKey) => {
    setAllergies([...allergies, key]);
    setNewAllergy("");
    setAllergyModalVisible(false);
  };

  // Fallback for anything not in the curated list — stores the raw
  // typed text, same as before this list existed.
  const addCondition = () => {
    const value = newCondition.trim();

    if (!value) {
      return;
    }

    if (conditions.some((item) => item.toLowerCase() === value.toLowerCase())) {
      return;
    }

    setConditions([...conditions, value]);

    setNewCondition("");
    setConditionModalVisible(false);
  };

  const addAllergy = () => {
    const value = newAllergy.trim();

    if (!value) {
      return;
    }

    if (allergies.some((item) => item.toLowerCase() === value.toLowerCase())) {
      return;
    }

    setAllergies([...allergies, value]);

    setNewAllergy("");
    setAllergyModalVisible(false);
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <TouchableOpacity
            style={styles.headerSideButton}
            onPress={() => router.back()}
          >
            <Ionicons name="chevron-back" size={24} color={Colours.text} />
          </TouchableOpacity>

          <Text
            style={styles.headerTitle}
            numberOfLines={1}
            ellipsizeMode="tail"
          >
            {t("medicalId.title")}
          </Text>

          <TouchableOpacity
            testID="medical-id-save-button"
            style={styles.headerSideButton}
            disabled={saving}
            onPress={handleSave}
          >
            <Text style={styles.saveText} numberOfLines={1}>
              {saving ? t("common.loading") : t("common.save")}
            </Text>
          </TouchableOpacity>
        </View>

        <View style={styles.profile}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={40} color={Colours.primary} />
          </View>

          <Text testID="medical-id-name-text" style={styles.name}>
            {fullName}
          </Text>

          <Text style={styles.subtitle}>{t("medicalId.emergencyProfile")}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t("medicalId.criticalInfo")}</Text>

          <View style={styles.card}>
            <Text style={styles.label}>{t("profile.bloodType")}</Text>

            <TouchableOpacity
              testID="medical-id-blood-type-trigger"
              style={styles.dropdown}
              onPress={() => setBloodTypeModalVisible(true)}
            >
              <Text>
                {bloodType ||
                  t("medicalId.selectBloodType", {
                    defaultValue: "Select blood type",
                  })}
              </Text>

              <Ionicons name="chevron-down" size={18} color={Colours.muted} />
            </TouchableOpacity>
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.sectionTitle}>
              {t("medicalId.medicalConditions")}
            </Text>

            <TouchableOpacity
              testID="medical-id-add-condition-button"
              onPress={() => setConditionModalVisible(true)}
            >
              <Ionicons name="add-circle" size={24} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {conditions.map((condition) => (
              <Tag
                key={condition}
                label={getConditionLabel(condition, currentLangCode)}
                onRemove={() => removeCondition(condition)}
                testID={`medical-id-remove-condition-${condition}`}
              />
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.sectionTitle}>{t("profile.allergies")}</Text>

            <TouchableOpacity
              testID="medical-id-add-allergy-button"
              onPress={() => setAllergyModalVisible(true)}
            >
              <Ionicons name="add-circle" size={24} color={Colours.danger} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {allergies.map((allergy) => (
              <Tag
                key={allergy}
                label={getAllergyLabel(allergy, currentLangCode)}
                onRemove={() => removeAllergy(allergy)}
                testID={`medical-id-remove-allergy-${allergy}`}
              />
            ))}
          </View>
        </View>
      </ScrollView>

      <Modal visible={conditionModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("medicalId.addCondition")}</Text>

            <TextInput
              testID="medical-id-condition-input"
              style={styles.input}
              value={newCondition}
              onChangeText={setNewCondition}
              placeholder={t("medicalId.conditionPlaceholder")}
            />

            {conditionSuggestions.length > 0 && (
              <ScrollView style={styles.suggestionsList}>
                {conditionSuggestions.map((key) => (
                  <TouchableOpacity
                    key={key}
                    testID={`medical-id-condition-suggestion-${key}`}
                    style={styles.suggestionRow}
                    onPress={() => selectConditionSuggestion(key)}
                  >
                    <Text style={styles.suggestionText}>
                      {medicalConditions[key][currentLangCode]}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}

            <View style={styles.modalActions}>
              <TouchableOpacity
                testID="medical-id-condition-cancel-button"
                onPress={() => {
                  setNewCondition("");
                  setConditionModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="medical-id-condition-add-button"
                onPress={addCondition}
              >
                <Text>{t("common.add")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={allergyModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("medicalId.addAllergy")}</Text>

            <TextInput
              testID="medical-id-allergy-input"
              style={styles.input}
              value={newAllergy}
              onChangeText={setNewAllergy}
              placeholder={t("medicalId.allergyPlaceholder")}
            />

            {allergySuggestions.length > 0 && (
              <ScrollView style={styles.suggestionsList}>
                {allergySuggestions.map((key) => (
                  <TouchableOpacity
                    key={key}
                    testID={`medical-id-allergy-suggestion-${key}`}
                    style={styles.suggestionRow}
                    onPress={() => selectAllergySuggestion(key)}
                  >
                    <Text style={styles.suggestionText}>
                      {allergyList[key][currentLangCode]}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
            )}

            <View style={styles.modalActions}>
              <TouchableOpacity
                testID="medical-id-allergy-cancel-button"
                onPress={() => {
                  setNewAllergy("");
                  setAllergyModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>

              <TouchableOpacity
                testID="medical-id-allergy-add-button"
                onPress={addAllergy}
              >
                <Text>{t("common.add")}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
      <Modal visible={bloodTypeModalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{t("profile.bloodType")}</Text>

            {BLOOD_TYPES.map((option) => (
              <TouchableOpacity
                key={option}
                testID={`medical-id-blood-type-option-${option}`}
                style={styles.bloodTypeOption}
                onPress={() => {
                  setBloodType(option === "Unknown" ? "" : option);
                  setBloodTypeModalVisible(false);
                }}
              >
                <Text style={styles.bloodTypeOptionText}>{option}</Text>

                {bloodType === option ||
                (option === "Unknown" && !bloodType) ? (
                  <Ionicons
                    name="checkmark"
                    size={20}
                    color={Colours.primary}
                  />
                ) : null}
              </TouchableOpacity>
            ))}

            <TouchableOpacity
              testID="medical-id-blood-type-cancel-button"
              style={styles.modalActions}
              onPress={() => setBloodTypeModalVisible(false)}
            >
              <Text>{t("common.cancel")}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function Tag({
  label,
  onRemove,
  testID,
}: {
  label: string;
  onRemove: () => void;
  testID?: string;
}) {
  return (
    <View style={styles.tag}>
      <Text style={styles.tagText}>{label}</Text>

      <TouchableOpacity testID={testID} onPress={onRemove}>
        <Ionicons name="close" size={16} color={Colours.muted} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colours.background,
  },

  content: {
    padding: 20,
    paddingBottom: 40,
  },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 32,
  },

  headerTitle: {
    ...Typography.h3,
    flex: 1,
    textAlign: "center",
    marginHorizontal: 8,
  },

  headerSideButton: {
    flexShrink: 0,
  },

  saveText: {
    color: Colours.primary,
    fontWeight: "700",
  },

  profile: {
    alignItems: "center",
    marginBottom: 32,
  },

  avatar: {
    width: 90,
    height: 90,
    borderRadius: 45,
    backgroundColor: Colours.surfaceLight,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 12,
  },

  name: {
    ...Typography.h3,
  },

  subtitle: {
    color: Colours.muted,
  },

  section: {
    marginBottom: 28,
  },

  sectionTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 12,
  },

  card: {
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 16,
    borderWidth: 1,
    borderColor: Colours.border,
  },

  label: {
    marginBottom: 10,
    color: Colours.muted,
  },

  dropdown: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },

  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },

  tagRow: {
    flexDirection: "row",
    flexWrap: "wrap",
  },

  tag: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colours.surfaceLight,
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginRight: 8,
    marginBottom: 8,
  },

  tagText: {
    marginRight: 6,
    color: Colours.text,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.5)",
  },

  modalCard: {
    width: "85%",
    backgroundColor: Colours.surface,
    borderRadius: 16,
    padding: 20,
  },

  modalTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 16,
  },

  input: {
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },

  suggestionsList: {
    maxHeight: 220,
    marginBottom: 16,
  },

  suggestionRow: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  suggestionText: {
    fontSize: 15,
    color: Colours.text,
  },

  modalActions: {
    flexDirection: "row",
    justifyContent: "space-between",
  },

  bloodTypeOption: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  bloodTypeOptionText: {
    fontSize: 16,
    color: Colours.text,
  },
});
