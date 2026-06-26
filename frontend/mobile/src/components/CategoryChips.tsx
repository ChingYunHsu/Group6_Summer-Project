
import {
    ScrollView,
    StyleSheet,
    Text,
    TouchableOpacity,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";

export type Category =
  | "Clinic"
  | "Pharmacy"
  | "AED";

interface Props {

  selected: Category;

  onSelect: (
    category: Category
  ) => void;

}

const categories: {
  label: Category;

  icon:
    | "medical"
    | "medkit"
    | "heart";

}[] = [

  {
    label: "Clinic",
    icon: "medical",
  },

  {
    label: "Pharmacy",
    icon: "medkit",
  },

  {
    label: "AED",
    icon: "heart",
  },

];

export default function CategoryChips({

  selected,

  onSelect,

}: Props) {

  return (

    <ScrollView

      horizontal

      showsHorizontalScrollIndicator={
        false
      }

      contentContainerStyle={
        styles.container
      }

    >

      {categories.map(
        (category) => {

          const active =
            selected ===
            category.label;

          return (

            <TouchableOpacity

              key={
                category.label
              }

              style={[
                styles.chip,

                active &&
                  styles.activeChip,
              ]}

              onPress={() =>
                onSelect(
                  category.label
                )
              }

            >

              <Ionicons

                name={
                  category.icon
                }

                size={18}

                color={
                  active
                    ? "#FFF"
                    : Colours.text
                }

              />

              <Text
                style={[
                  styles.text,

                  active &&
                    styles.activeText,
                ]}
              >

                {
                  category.label
                }

              </Text>

            </TouchableOpacity>

          );

        }
      )}

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

    backgroundColor:
      "#FFFFFF",

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

    backgroundColor:
      Colours.primary,

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