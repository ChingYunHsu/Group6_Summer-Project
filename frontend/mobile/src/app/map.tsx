import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useState } from "react";
import {
    FlatList,
    SafeAreaView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

const mockVenues = [
  {
    id: "1",
    name: "CityMD Urgent Care",
    category: "Clinic",
    distance: "0.4 mi",
  },
  {
    id: "2",
    name: "CVS Pharmacy",
    category: "Pharmacy",
    distance: "0.7 mi",
  },
  {
    id: "3",
    name: "Times Square AED",
    category: "AED",
    distance: "0.2 mi",
  },
];

const categories = [
  "All",
  "Clinic",
  "Pharmacy",
  "AED",
];

export default function MapScreen() {
  const [search, setSearch] =
    useState("");

  const [selectedCategory, setSelectedCategory] =
    useState("All");

  const filteredVenues =
    mockVenues.filter((venue) => {
      const matchesSearch =
        venue.name
          .toLowerCase()
          .includes(
            search.toLowerCase()
          );

      const matchesCategory =
        selectedCategory === "All" ||
        venue.category ===
          selectedCategory;

      return (
        matchesSearch &&
        matchesCategory
      );
    });

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}

      <View style={styles.header}>
        <Text style={styles.title}>
          Find Care
        </Text>

        <TouchableOpacity
          onPress={() =>
            router.push("/profile")
          }
        >
          <Ionicons
            name="person-circle"
            size={34}
            color={Colours.primary}
          />
        </TouchableOpacity>
      </View>

      {/* Search */}

      <View style={styles.searchContainer}>
        <Ionicons
          name="search"
          size={20}
          color={Colours.muted}
        />

        <TextInput
          style={styles.searchInput}
          placeholder="Search clinics or pharmacies..."
          placeholderTextColor={
            Colours.muted
          }
          value={search}
          onChangeText={setSearch}
        />

        <TouchableOpacity>
          <Ionicons
            name="options"
            size={20}
            color={Colours.primary}
          />
        </TouchableOpacity>
      </View>

      {/* Categories */}

      <View style={styles.chipsRow}>
        {categories.map(
          (category) => (
            <TouchableOpacity
              key={category}
              style={[
                styles.chip,
                selectedCategory ===
                  category &&
                  styles.selectedChip,
              ]}
              onPress={() =>
                setSelectedCategory(
                  category
                )
              }
            >
              <Text
                style={[
                  styles.chipText,
                  selectedCategory ===
                    category &&
                    styles.selectedChipText,
                ]}
              >
                {category}
              </Text>
            </TouchableOpacity>
          )
        )}
      </View>

      {/* Placeholder Map */}

      <View style={styles.mapPlaceholder}>
        <Ionicons
          name="map"
          size={60}
          color={Colours.primary}
        />

        <Text
          style={styles.mapPlaceholderText}
        >
          Interactive Map
        </Text>

        <Text
          style={styles.mapPlaceholderSubtext}
        >
          React Native Maps integration
          coming next.
        </Text>
      </View>

      {/* Nearby Venues */}

      <Text style={styles.sectionTitle}>
        Nearby Facilities
      </Text>

      <FlatList
        data={filteredVenues}
        keyExtractor={(item) =>
          item.id
        }
        showsVerticalScrollIndicator={
          false
        }
        renderItem={({ item }) => (
          <View
            style={styles.venueCard}
          >
            <Ionicons
              name="medical"
              size={24}
              color={
                Colours.primary
              }
            />

            <View
              style={
                styles.venueInfo
              }
            >
              <Text
                style={
                  styles.venueName
                }
              >
                {item.name}
              </Text>

              <Text
                style={
                  styles.venueMeta
                }
              >
                {item.category} •{" "}
                {item.distance}
              </Text>
            </View>
          </View>
        )}
      />

      {/* Report Button */}

      <TouchableOpacity
        style={styles.reportButton}
      >
        <Ionicons
          name="warning"
          size={22}
          color="#FFFFFF"
        />
      </TouchableOpacity>

      {/* SOS Button */}

      <TouchableOpacity
        style={styles.sosButton}
        onPress={() =>
          router.push("/sos")
        }
      >
        <Text style={styles.sosText}>
          SOS
        </Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor:
      Colours.background,
    padding: 20,
  },

  header: {
    flexDirection: "row",
    justifyContent:
      "space-between",
    alignItems: "center",
    marginBottom: 16,
  },

  title: {
    ...Typography.h1,
  },

  searchContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor:
      Colours.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    paddingHorizontal: 14,
    marginBottom: 16,
  },

  searchInput: {
    flex: 1,
    height: 50,
    marginLeft: 10,
    color: Colours.text,
  },

  chipsRow: {
    flexDirection: "row",
    marginBottom: 20,
  },

  chip: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 999,
    backgroundColor:
      Colours.surface,
    marginRight: 8,
  },

  selectedChip: {
    backgroundColor:
      Colours.primary,
  },

  chipText: {
    color: Colours.text,
  },

  selectedChipText: {
    color: "#FFFFFF",
    fontWeight: "700",
  },

  mapPlaceholder: {
    height: 220,
    borderRadius: 20,
    backgroundColor:
      Colours.surface,
    borderWidth: 1,
    borderColor: Colours.border,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 20,
  },

  mapPlaceholderText: {
    ...Typography.h3,
    marginTop: 10,
  },

  mapPlaceholderSubtext: {
    color: Colours.muted,
    marginTop: 4,
  },

  sectionTitle: {
    ...Typography.body,
    fontWeight: "700",
    marginBottom: 12,
  },

  venueCard: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor:
      Colours.surface,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: Colours.border,
    padding: 16,
    marginBottom: 10,
  },

  venueInfo: {
    marginLeft: 12,
  },

  venueName: {
    fontWeight: "700",
    color: Colours.text,
  },

  venueMeta: {
    color: Colours.muted,
    marginTop: 2,
  },

  reportButton: {
    position: "absolute",
    right: 24,
    bottom: 110,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#F59E0B",
    justifyContent: "center",
    alignItems: "center",
    elevation: 5,
  },

  sosButton: {
    position: "absolute",
    right: 24,
    bottom: 36,
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: "#DC2626",
    justifyContent: "center",
    alignItems: "center",
    elevation: 5,
  },

  sosText: {
    color: "#FFFFFF",
    fontWeight: "800",
    fontSize: 18,
  },
});