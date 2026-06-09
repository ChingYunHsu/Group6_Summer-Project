import { useRouter } from "expo-router";
import { useMemo, useState } from "react";
import {
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  allLanguages,
  featuredLanguages,
} from "../data/languages";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

console.log("Colours import:", Colours);

export default function LanguageScreen() {
  const router = useRouter();

  const [search, setSearch] = useState("");

  const [selectedLanguage, setSelectedLanguage] =
    useState<{
      native: string;
      english: string;
      flag?: string;
    }>(featuredLanguages[0]);

  const filteredLanguages = useMemo(() => {
    if (!search.trim()) return [];

    return allLanguages.filter(
      (language) =>
        language.native
          .toLowerCase()
          .includes(search.toLowerCase()) ||
        language.english
          .toLowerCase()
          .includes(search.toLowerCase())
    );
  }, [search]);

  const isFeaturedLanguage =
    featuredLanguages.some(
      (lang) =>
        lang.english ===
        selectedLanguage?.english
    );

  return (
    <View style={styles.container}>
      <Text style={styles.title}>
        Choose your language
      </Text>

      <TextInput
        placeholder="Search other languages..."
        value={search}
        onChangeText={setSearch}
        style={styles.searchInput}
        placeholderTextColor={Colours.muted}
      />

      {selectedLanguage &&
        !isFeaturedLanguage && (
          <View
            style={
              styles.selectedContainer
            }
          >
            <Text
              style={styles.selectedLabel}
            >
              Selected Language
            </Text>

            <Text
              style={styles.selectedValue}
            >
              {selectedLanguage.native}
            </Text>

            <Text style={styles.english}>
              {selectedLanguage.english}
            </Text>
          </View>
        )}

      {search.length > 0 && (
        <View style={styles.searchResults}>
          {filteredLanguages.map(
            (language) => (
              <TouchableOpacity
                key={language.english}
                style={styles.resultRow}
                onPress={() => {
                  setSelectedLanguage(
                    language
                  );
                  setSearch("");
                }}
              >
                <Text
                  style={styles.resultText}
                >
                  {language.native} (
                  {language.english})
                </Text>
              </TouchableOpacity>
            )
          )}
        </View>
      )}

      <FlatList
        data={featuredLanguages}
        numColumns={2}
        keyExtractor={(item) =>
          item.english
        }
        renderItem={({ item }) => {
          const selected =
            selectedLanguage?.english ===
            item.english;

          return (
            <TouchableOpacity
              style={[
                styles.card,
                selected &&
                  styles.selectedCard,
              ]}
              onPress={() =>
                setSelectedLanguage(item)
              }
            >
              {selected && (
                <View
                  style={styles.checkmark}
                >
                  <Text
                    style={
                      styles.checkmarkText
                    }
                  >
                    ✓
                  </Text>
                </View>
              )}

              <Text style={styles.flag}>
                {item.flag}
              </Text>

              <Text style={styles.native}>
                {item.native}
              </Text>

              <Text style={styles.english}>
                {item.english}
              </Text>
            </TouchableOpacity>
          );
        }}
      />

      <TouchableOpacity
        style={styles.button}
        onPress={() =>
          router.push("/legal")
        }
      >
        <Text style={styles.buttonText}>
          Continue
        </Text>
      </TouchableOpacity>

      <Text style={styles.footer}>
        By continuing, you will review
        our{" "}
        <Text style={styles.linkText}>
          Terms of Service
        </Text>{" "}
        and{" "}
        <Text style={styles.linkText}>
          Privacy Policy
        </Text>
        .
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    paddingTop: 80,
    backgroundColor: Colours.surface,
  },

  title: {
    ...Typography.h2,
    color: Colours.text,
    textAlign: "center",
    marginBottom: 24,
  },

  searchInput: {
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    padding: 14,
    marginBottom: 12,
    backgroundColor: Colours.surface,
    color: Colours.text,
  },

  searchResults: {
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    marginBottom: 16,
    maxHeight: 250,
    backgroundColor: Colours.surface,
  },

  resultRow: {
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  resultText: {
    ...Typography.body,
    color: Colours.text,
  },

  card: {
    flex: 1,
    margin: 8,
    borderWidth: 1,
    borderColor: Colours.border,
    borderRadius: 12,
    padding: 20,
    position: "relative",
    backgroundColor: Colours.surface,
  },

  selectedCard: {
    borderColor: Colours.primary,
    borderWidth: 2,
  },

  checkmark: {
    position: "absolute",
    top: 10,
    right: 10,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colours.primary,
    justifyContent: "center",
    alignItems: "center",
  },

  checkmarkText: {
    color: Colours.surface,
    fontWeight: "700",
  },

  flag: {
    fontSize: 28,
    marginBottom: 12,
  },

  native: {
    ...Typography.h3,
    color: Colours.text,
  },

  english: {
    ...Typography.bodySmall,
    color: Colours.muted,
    marginTop: 4,
  },

  button: {
    backgroundColor: Colours.primary,
    padding: 18,
    borderRadius: 30,
    marginTop: 20,
  },

  buttonText: {
    ...Typography.button,
    color: Colours.surface,
    textAlign: "center",
  },

  footer: {
    ...Typography.caption,
    textAlign: "center",
    color: Colours.muted,
    marginTop: 16,
    marginBottom: 30,
    lineHeight: 18,
  },

  linkText: {
    color: Colours.primary,
    fontWeight: "700",
  },

  selectedContainer: {
    backgroundColor: Colours.surfaceLight,
    borderWidth: 1,
    borderColor: Colours.borderLight,
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
  },

  selectedLabel: {
    ...Typography.caption,
    color: Colours.primary,
    fontWeight: "600",
  },

  selectedValue: {
    ...Typography.body,
    color: Colours.text,
    fontWeight: "700",
    marginTop: 4,
  },
});