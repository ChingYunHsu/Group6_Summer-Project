import { ScrollView, StyleSheet, Text, TouchableOpacity } from "react-native";

import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { Colours } from "../constants/colours";

export type Category = "Clinic" | "Pharmacy" | "AED" | "Hospital" | "Restroom";

// label stays the stable internal value (matched against in map.tsx's
// filter switch) — translationKey drives what's actually displayed.
// Previously label was used directly as display text too, so this chip
// row never responded to language changes at all.
const categories: {
  label: Category;

  translationKey: string;

  icon: "medical" | "medkit" | "heart" | "business" | "male-female";
}[] = [
  {
    label: "Clinic",
    translationKey: "map.categories.clinic",
    icon: "medical",
  },

  {
    label: "Pharmacy",
    translationKey: "map.categories.pharmacy",
    icon: "medkit",
  },

  {
    label: "AED",
    translationKey: "map.categories.aed",
    icon: "heart",
  },

  {
    label: "Hospital",
    translationKey: "map.categories.hospital",
    icon: "business",
  },

  {
    label: "Restroom",
    translationKey: "map.categories.restroom",
    icon: "male-female",
  },
];

interface Props {
  selected: Category;

  onSelect: (category: Category) => void;
}

export default function CategoryChips({ selected, onSelect }: Props) {
  const { t } = useTranslation();

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.container}
    >
      {categories.map((category) => {
        const active = selected === category.label;

        return (
          <TouchableOpacity
            key={category.label}
            style={[styles.chip, active && styles.activeChip]}
            onPress={() => onSelect(category.label)}
          >
            <Ionicons
              name={category.icon}
              size={18}
              color={active ? "#FFF" : Colours.text}
            />

            <Text style={[styles.text, active && styles.activeText]}>
              {t(category.translationKey, { defaultValue: category.label })}
            </Text>
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: 14,

    paddingBottom: 4,

    paddingRight: 20,
  },

  chip: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 999,

    paddingHorizontal: 18,

    paddingVertical: 10,

    marginRight: 12,

    shadowColor: "#000",

    shadowOpacity: 0.08,

    shadowRadius: 6,

    shadowOffset: {
      width: 0,

      height: 2,
    },

    elevation: 3,
  },

  activeChip: {
    backgroundColor: Colours.primary,
  },

  text: {
    marginLeft: 8,

    fontSize: 15,

    fontWeight: "600",

    color: Colours.text,
  },

  activeText: {
    color: "#FFF",
  },
});
