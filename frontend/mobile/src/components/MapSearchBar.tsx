import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";
import {
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { Colours } from "../constants/colours";
import { Venue } from "../types/venue";

interface Props {
  value: string;

  onChangeText: (text: string) => void;

  onFilterPress: () => void;

  // Optional: when provided alongside a non-empty value, renders a
  // dropdown of matching venues below the search bar — mirrors the
  // search-results pattern already used in language.tsx. Both omitted
  // (map.tsx not yet updated) keeps this exactly as before, so this is
  // a non-breaking addition.
  suggestions?: Venue[];

  onSelectSuggestion?: (venue: Venue) => void;
}

export default function MapSearchBar({
  value,

  onChangeText,

  onFilterPress,

  suggestions = [],

  onSelectSuggestion,
}: Props) {
  const { t } = useTranslation();

  const showDropdown = value.trim().length > 0 && suggestions.length > 0;

  return (
    <View style={styles.wrapper}>
      <View style={styles.container}>
        <Ionicons name="search" size={20} color={Colours.muted} />

        <TextInput
          testID="map-search-input"
          value={value}
          onChangeText={onChangeText}
          placeholder={t("map.searchPlaceholder")}
          placeholderTextColor={Colours.muted}
          autoCorrect={false}
          autoCapitalize="none"
          style={styles.input}
          returnKeyType="search"
        />

        <TouchableOpacity testID="map-filter-button" onPress={onFilterPress}>
          <Ionicons name="options" size={22} color={Colours.primary} />
        </TouchableOpacity>
      </View>

      {/* keyboardShouldPersistTaps="handled" is required here — without
          it, tapping a row first dismisses the keyboard/blurs the
          TextInput rather than registering the row's onPress, a common
          RN gotcha with search dropdowns specifically. */}
      {showDropdown && (
        <FlatList
          style={styles.dropdown}
          keyboardShouldPersistTaps="handled"
          data={suggestions}
          keyExtractor={(item) => item.venue_id}
          renderItem={({ item }) => (
            <TouchableOpacity
              testID={`map-search-suggestion-${item.venue_id}`}
              style={styles.dropdownRow}
              onPress={() => onSelectSuggestion?.(item)}
            >
              <Ionicons name="location" size={16} color={Colours.primary} />

              <View style={styles.dropdownTextContainer}>
                <Text style={styles.dropdownName} numberOfLines={1}>
                  {item.name}
                </Text>

                {!!item.address && (
                  <Text style={styles.dropdownAddress} numberOfLines={1}>
                    {item.address}
                  </Text>
                )}
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    // Deliberately not `overflow: hidden` — the dropdown is an absolute-
    // positioned overlay below the search bar, not a child that
    // participates in the wrapper's own layout height.
  },

  container: {
    flexDirection: "row",

    alignItems: "center",

    backgroundColor: "#FFFFFF",

    borderRadius: 18,

    paddingHorizontal: 16,

    height: 56,

    shadowColor: "#000",

    shadowOpacity: 0.12,

    shadowRadius: 10,

    shadowOffset: {
      width: 0,

      height: 3,
    },

    elevation: 6,
  },

  input: {
    flex: 1,

    marginLeft: 12,

    color: Colours.text,

    fontSize: 16,
  },

  // Positioned as an overlay directly below the search bar (height 56 +
  // small gap), so it floats over the map rather than pushing the
  // category chips (rendered right after this component in map.tsx)
  // further down.
  dropdown: {
    position: "absolute",
    top: 62,
    left: 0,
    right: 0,
    maxHeight: 260,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
    zIndex: 20,
  },

  dropdownRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colours.border,
  },

  dropdownTextContainer: {
    marginLeft: 10,
    flex: 1,
  },

  dropdownName: {
    fontSize: 15,
    fontWeight: "600",
    color: Colours.text,
  },

  dropdownAddress: {
    fontSize: 12,
    color: Colours.muted,
    marginTop: 2,
  },
});
