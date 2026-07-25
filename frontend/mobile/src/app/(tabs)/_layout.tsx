import { Ionicons } from "@expo/vector-icons";
import { Tabs } from "expo-router";
import { useTranslation } from "react-i18next";

import { Colours } from "../../constants/colours";

export default function TabLayout() {
  const { t } = useTranslation();

  return (
    <Tabs
      screenOptions={{
        headerTitleAlign: "center",
        headerStyle: {
          backgroundColor: Colours.surface,
        },
        headerTintColor: Colours.text,

        tabBarActiveTintColor: Colours.primary,
        tabBarInactiveTintColor: Colours.muted,

        // Hides the bottom tab bar whenever the software keyboard is
        // open. Without this, KeyboardAvoidingView on screens like
        // Assistant and Show Staff can't correctly calculate how much
        // to push content up on iOS — the tab bar reserves its own
        // space at the true bottom of the screen, and that extra gap
        // between the tab screen's own bottom edge and the physical
        // screen edge throws off KeyboardAvoidingView's padding math.
        // This is Expo's own documented fix for exactly this
        // combination (bottom tabs + KeyboardAvoidingView), not a
        // cosmetic preference.
        tabBarHideOnKeyboard: true,

        tabBarStyle: {
          height: 78,
          paddingTop: 8,
          paddingBottom: 12,
          borderTopWidth: 0,
          elevation: 10,
          backgroundColor: Colours.surface,
        },

        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
        },
      }}
    >
      <Tabs.Screen
        name="map"
        options={{
          title: t("tabs.map"),
          headerTitle: t("tabs.hospitalMap"),
          tabBarButtonTestID: "tab-map",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="map-outline" color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="assistant"
        options={{
          title: t("tabs.assistant"),
          headerTitle: t("tabs.clearPathAssistant"),
          tabBarButtonTestID: "tab-assistant",
          tabBarIcon: ({ color, size }) => (
            <Ionicons
              name="chatbubble-ellipses-outline"
              color={color}
              size={size}
            />
          ),
        }}
      />

      <Tabs.Screen
        name="show-staff"
        options={{
          title: t("tabs.showStaff"),
          headerShown: false,
          tabBarButtonTestID: "tab-show-staff",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="profile"
        options={{
          title: t("tabs.profile"),
          headerTitle: t("tabs.myProfile"),
          tabBarButtonTestID: "tab-profile",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-circle-outline" color={color} size={size} />
          ),
        }}
      />

      <Tabs.Screen
        name="more"
        options={{
          title: t("tabs.more"),
          headerTitle: t("tabs.more"),
          tabBarButtonTestID: "tab-more",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="menu-outline" color={color} size={size} />
          ),
        }}
      />
    </Tabs>
  );
}
