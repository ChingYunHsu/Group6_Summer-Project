import { useState } from "react";

import {
    LayoutAnimation,
    Platform,
    StyleSheet,
    Text,
    TouchableOpacity,
    UIManager,
    View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";

if (
  Platform.OS === "android" &&
  UIManager.setLayoutAnimationEnabledExperimental
) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

interface Props {
  stepNumber: number;
  title: string;
}

export default function RouteStep({
  stepNumber,
  title,
}: Props) {
  const [expanded, setExpanded] =
    useState(false);

  function toggleExpanded() {
    LayoutAnimation.configureNext(
      LayoutAnimation.Presets.easeInEaseOut
    );

    setExpanded(current => !current);
  }

  return (
    <View style={styles.container}>

      <TouchableOpacity
        style={styles.header}
        activeOpacity={0.8}
        onPress={toggleExpanded}
      >

        <View style={styles.numberCircle}>

          <Text style={styles.number}>
            {stepNumber}
          </Text>

        </View>

        <View style={styles.textContainer}>

          <Text style={styles.title}>
            {title}
          </Text>

        </View>

        <Ionicons
          name={
            expanded
              ? "chevron-up"
              : "chevron-down"
          }
          size={22}
          color={Colours.primary}
        />

      </TouchableOpacity>

      {expanded && (

        <View style={styles.detailContainer}>

          <Text style={styles.detailText}>
            {title}
          </Text>

        </View>

      )}

    </View>
  );
}

const styles = StyleSheet.create({

  container: {

    borderRadius: 18,

    backgroundColor: "#FFFFFF",

    borderWidth: 1,

    borderColor: "#E5E7EB",

    marginBottom: 12,

    overflow: "hidden",

  },

  header: {

    flexDirection: "row",

    alignItems: "center",

    padding: 16,

  },

  numberCircle: {

    width: 34,

    height: 34,

    borderRadius: 17,

    backgroundColor: Colours.primary,

    justifyContent: "center",

    alignItems: "center",

    marginRight: 14,

  },

  number: {

    color: "#FFFFFF",

    fontWeight: "700",

    fontSize: 15,

  },

  textContainer: {

    flex: 1,

  },

  title: {

    fontSize: 15,

    fontWeight: "600",

    color: Colours.text,

  },

  detailContainer: {

    borderTopWidth: 1,

    borderTopColor: "#F3F4F6",

    paddingHorizontal: 16,

    paddingVertical: 14,

    backgroundColor: "#FAFAFA",

  },

  detailText: {

    color: "#6B7280",

    lineHeight: 22,

    fontSize: 14,

  },

});