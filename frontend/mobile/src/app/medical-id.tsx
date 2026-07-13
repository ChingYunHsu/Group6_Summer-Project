import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useEffect, useState } from "react";
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

export default function MedicalIdScreen() {
  const { t } = useTranslation();

  const [conditionModalVisible, setConditionModalVisible] = useState(false);

  const [allergyModalVisible, setAllergyModalVisible] = useState(false);

  const [bloodTypeModalVisible, setBloodTypeModalVisible] = useState(false);

  const [newCondition, setNewCondition] = useState("");

  const [newAllergy, setNewAllergy] = useState("");

  // mockMedicalId is no longer a valid seed here — see the comment on
  // DEFAULT_MEDICAL_PROFILE in medicalIdService.ts for why (it's shaped
  // like the old MedicalId interface, missing date_of_birth/gender/
  // address/emergency_contacts that MedicalProfile requires).
  const [medicalId, setMedicalId] = useState<MedicalProfile>(
    DEFAULT_MEDICAL_PROFILE,
  );

  // Previously there were two separate state variables here — fullName
  // (correctly populated from the fetch, but never rendered) and
  // displayName (rendered in the JSX, but setDisplayName was never called
  // anywhere) — so the name shown on this screen was permanently blank
  // regardless of who was logged in. Consolidated to one.
  const [fullName, setFullName] = useState("");

  const [bloodType, setBloodType] = useState(medicalId.blood_type);

  const [conditions, setConditions] = useState(medicalId.conditions);

  const [saving, setSaving] = useState(false);

  const [allergies, setAllergies] = useState(medicalId.allergies ?? []);

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
        {/* Header */}

        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="chevron-back" size={24} color={Colours.text} />
          </TouchableOpacity>

          <Text style={styles.headerTitle}>{t("medicalId.title")}</Text>

          <TouchableOpacity disabled={saving} onPress={handleSave}>
            <Text style={styles.saveText}>
              {saving ? t("common.loading") : t("common.save")}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Profile */}

        <View style={styles.profile}>
          <View style={styles.avatar}>
            <Ionicons name="person" size={40} color={Colours.primary} />
          </View>

          <Text style={styles.name}>{fullName}</Text>

          <Text style={styles.subtitle}>{t("medicalId.emergencyProfile")}</Text>
        </View>

        {/* Blood Type */}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>{t("medicalId.criticalInfo")}</Text>

          <View style={styles.card}>
            <Text style={styles.label}>{t("profile.bloodType")}</Text>

            <TouchableOpacity
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

        {/* Conditions */}

        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.sectionTitle}>
              {t("medicalId.medicalConditions")}
            </Text>

            <TouchableOpacity onPress={() => setConditionModalVisible(true)}>
              <Ionicons name="add-circle" size={24} color={Colours.primary} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {conditions.map((condition) => (
              <Tag
                key={condition}
                label={condition}
                onRemove={() => removeCondition(condition)}
              />
            ))}
          </View>
        </View>

        {/* Allergies */}

        <View style={styles.section}>
          <View style={styles.row}>
            <Text style={styles.sectionTitle}>{t("profile.allergies")}</Text>

            <TouchableOpacity onPress={() => setAllergyModalVisible(true)}>
              <Ionicons name="add-circle" size={24} color={Colours.danger} />
            </TouchableOpacity>
          </View>

          <View style={styles.tagRow}>
            {allergies.map((allergy) => (
              <Tag
                key={allergy}
                label={allergy}
                onRemove={() => removeAllergy(allergy)}
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
              style={styles.input}
              value={newCondition}
              onChangeText={setNewCondition}
              placeholder={t("medicalId.conditionPlaceholder")}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => {
                  setNewCondition("");
                  setConditionModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={addCondition}>
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
              style={styles.input}
              value={newAllergy}
              onChangeText={setNewAllergy}
              placeholder={t("medicalId.allergyPlaceholder")}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                onPress={() => {
                  setNewAllergy("");
                  setAllergyModalVisible(false);
                }}
              >
                <Text>{t("common.cancel")}</Text>
              </TouchableOpacity>

              <TouchableOpacity onPress={addAllergy}>
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

function Tag({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <View style={styles.tag}>
      <Text style={styles.tagText}>{label}</Text>

      <TouchableOpacity onPress={onRemove}>
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
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 32,
  },

  headerTitle: {
    ...Typography.h3,
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
