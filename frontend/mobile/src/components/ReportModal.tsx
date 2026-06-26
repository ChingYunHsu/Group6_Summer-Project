import { useMemo, useState } from "react";

import {
    Alert,
    Modal,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    TouchableOpacity,
    View,
} from "react-native";

import { Ionicons } from "@expo/vector-icons";

import { Colours } from "../constants/colours";
import { Typography } from "../constants/typography";

import { Venue } from "../types/venue";


interface Props {
    visible: boolean;

    isAuthenticated: boolean;
    locationEnabled: boolean;

    currentLocation: {
        latitude: number;
        longitude: number;
    };

    nearbyVenues: Venue[];

    onClose: () => void;

    onRequireLogin: () => void;

    onRequireLocation: () =>void;

    onSubmitVenue: (report: {
        venueId: string;
        issueType: string;
        description: string;
        timestamp: string;
    }) => void;

    onSubmitIncident: (report: {
        latitude: number;
        longitude: number;
        issueType: string;
        description: string;
        timestamp: string;
    }) => void;
}

type ReportMode =
    | "venue"
    | "incident"
    | null;

const ISSUE_TYPES = [
    {
        label: "Too Crowded",
        value: "large_crowd",
        icon: "people",
    },
    {
        label: "Entrance Blocked",
        value: "entrance_closed",
        icon: "close-circle",
    },
    {
        label: "Elevator Broken",
        value: "elevator_broken",
        icon: "warning",
    },
    {
        label: "Wheelchair Lift Broken",
        value: "wheelchair_lift_broken",
        icon: "construct",
    },
    {
        label: "Toilet Out of Order",
        value: "toilet_out_of_order",
        icon: "ban",
    },
    {
        label: "Protest / Blockage",
        value: "protest_or_blockage",
        icon: "alert-circle",
    },
    {
        label: "Hazard",
        value: "hazard",
        icon: "alert",
    },
    {
        label: "Other",
        value: "other",
        icon: "help-circle",
    },
] as const;

const ISSUE_FILTERS = {
    clinic: [
        "large_crowd",
        "entrance_closed",
        "elevator_broken",
        "wheelchair_lift_broken",
        "toilet_out_of_order",
        "hazard",
    ],

    hospital: [
        "large_crowd",
        "entrance_closed",
        "elevator_broken",
        "wheelchair_lift_broken",
        "toilet_out_of_order",
        "hazard",
    ],

    toilet: [
        "toilet_out_of_order",
        "entrance_closed",
        "hazard",
    ],

    transport: [
        "large_crowd",
        "entrance_closed",
        "protest_or_blockage",
        "hazard",
    ],

    building: [
        "entrance_closed",
        "elevator_broken",
        "wheelchair_lift_broken",
        "hazard",
    ],
};

export default function ReportModal({
    visible,
    onClose,

    isAuthenticated,
    locationEnabled,

    currentLocation,

    nearbyVenues,

    onRequireLogin,
    onRequireLocation,

    onSubmitVenue,
    onSubmitIncident,
}: Props) {

    const [mode, setMode] =
        useState<ReportMode>(null);

    const [selectedVenue, setSelectedVenue] =
        useState<string>("");

    const [issueType, setIssueType] =
        useState("");

    const [description, setDescription] =
        useState("");

    const selectedVenueObject =
        nearbyVenues.find(
            v => v.venue_id === selectedVenue
        );

    const visibleIssues = useMemo(() => {
    if (mode !== "venue") {
        return ISSUE_TYPES;
    }

    if (!selectedVenueObject) {
        return [];
    }

    const venueType =
    selectedVenueObject.venue_type as keyof typeof ISSUE_FILTERS;

const allowed =
    ISSUE_FILTERS[venueType] ?? ISSUE_TYPES.map(i => i.value);

    return ISSUE_TYPES.filter(issue =>
        allowed.includes(issue.value)
    );
}, [mode, selectedVenueObject]);

    const resetState = () => {

        setMode(null);
        setSelectedVenue("");
        setIssueType("");
        setDescription("");

    };

    const handleClose = () => {

        resetState();
        onClose();

    };

    const handleSubmit = () => {

        if (!isAuthenticated) {

            Alert.alert(
                "Login Required",
                "To help keep ClearPath data accurate, you must be logged in before submitting reports.",
                [
                    {
                        text: "Login",
                        onPress: () => {
                            handleClose();
                            onRequireLogin();
                        },
                    },
                ]
            );

            return;
        }

        if (!locationEnabled) {

            Alert.alert(
                "Location Services Required",
                "Please enable Location Services before submitting a report.",
                [
                    {
                        text: "OK",
                        onPress: onRequireLocation,
                    },
                ]
            );

            return;
        }

        if (!mode) {
            return;
        }

        if (!issueType) {
            return;
        }

        const timestamp =
            new Date().toISOString();

        if (mode === "venue") {

            if (!selectedVenue) {
                return;
            }

            onSubmitVenue({

                venueId: selectedVenue,

                issueType,

                description,

                timestamp,

            });

        } else {

            onSubmitIncident({

                latitude:
                    currentLocation.latitude,

                longitude:
                    currentLocation.longitude,

                issueType,

                description,

                timestamp,

            });

        }

        handleClose();

    };
        return (
        <Modal
            visible={visible}
            transparent
            animationType="slide"
            onRequestClose={handleClose}
        >
            <View style={styles.overlay}>
                <View style={styles.sheet}>

                    <View style={styles.handle} />

                    <View style={styles.header}>

                        <Text style={styles.title}>
                            Report an Issue
                        </Text>

                        <TouchableOpacity
                            onPress={handleClose}
                        >
                            <Ionicons
                                name="close"
                                size={26}
                                color={Colours.text}
                            />
                        </TouchableOpacity>

                    </View>

                    <Text style={styles.subtitle}>
                        Help keep ClearPath accurate by reporting a temporary accessibility issue.
                    </Text>

                    <ScrollView
                        showsVerticalScrollIndicator={false}
                    >

                        {/* ------------------------- */}
                        {/* STEP 1 */}
                        {/* ------------------------- */}

                        <Text style={styles.sectionTitle}>
                            Where is the issue?
                        </Text>

                        <View style={styles.modeContainer}>

                            <TouchableOpacity
                                style={[
                                    styles.modeCard,
                                    mode === "venue" &&
                                        styles.selectedCard,
                                ]}
                                onPress={() =>
                                    setMode("venue")
                                }
                            >

                                <Ionicons
                                    name="business"
                                    size={28}
                                    color={
                                        mode === "venue"
                                            ? "#FFFFFF"
                                            : Colours.primary
                                    }
                                />

                                <Text
                                    style={[
                                        styles.cardText,
                                        mode === "venue" &&
                                            styles.selectedCardText,
                                    ]}
                                >
                                    Nearby Landmark{"\n"}or Venue
                                </Text>

                            </TouchableOpacity>

                            <TouchableOpacity
                                style={[
                                    styles.modeCard,
                                    mode === "incident" &&
                                        styles.selectedCard,
                                ]}
                                onPress={() =>
                                    setMode("incident")
                                }
                            >

                                <Ionicons
                                    name="location"
                                    size={28}
                                    color={
                                        mode === "incident"
                                            ? "#FFFFFF"
                                            : Colours.primary
                                    }
                                />

                                <Text
                                    style={[
                                        styles.cardText,
                                        mode === "incident" &&
                                            styles.selectedCardText,
                                    ]}
                                >
                                    Drop Pin{"\n"}at Current Location
                                </Text>

                            </TouchableOpacity>

                        </View>

                        {/* ------------------------- */}
                        {/* STEP 2 */}
                        {/* ------------------------- */}

                        {mode === "venue" && (

                            <>
                                <Text
                                    style={styles.sectionTitle}
                                >
                                    Select Venue
                                </Text>

                                {nearbyVenues.map(
                                    venue => {

                                        const selected =
                                            selectedVenue ===
                                            venue.venue_id;

                                        return (

                                            <TouchableOpacity
                                                key={venue.venue_id}
                                                style={[
                                                    styles.venueRow,
                                                    selected &&
                                                        styles.selectedVenue,
                                                ]}
                                                onPress={() =>
                                                    setSelectedVenue(
                                                        venue.venue_id
                                                    )
                                                }
                                            >

                                                <View>

                                                    <Text
                                                        style={
                                                            styles.venueName
                                                        }
                                                    >
                                                        {venue.name}
                                                    </Text>

                                                    <Text
                                                        style={
                                                            styles.venueDistance
                                                        }
                                                    >
                                                        Nearby
                                                    </Text>

                                                </View>

                                                {selected && (
                                                    <Ionicons
                                                        name="checkmark-circle"
                                                        size={24}
                                                        color={
                                                            Colours.primary
                                                        }
                                                    />
                                                )}

                                            </TouchableOpacity>

                                        );

                                    }
                                )}

                            </>

                        )}

                        {/* ------------------------- */}
                        {/* STEP 3 */}
                        {/* ------------------------- */}

                        {mode !== null && (

                            <>
                                <Text
                                    style={styles.sectionTitle}
                                >
                                    Issue Type
                                </Text>

                                <View
                                    style={styles.grid}
                                >

                                    {visibleIssues.map(
                                        item => {

                                            const selected =
                                                issueType ===
                                                item.value;

                                            return (

                                                <TouchableOpacity
                                                    key={
                                                        item.value
                                                    }
                                                    style={[
                                                        styles.card,
                                                        selected &&
                                                            styles.selectedCard,
                                                    ]}
                                                    onPress={() =>
                                                        setIssueType(
                                                            item.value
                                                        )
                                                    }
                                                >

                                                    <Ionicons
                                                        name={
                                                            item.icon as any
                                                        }
                                                        size={
                                                            22
                                                        }
                                                        color={
                                                            selected
                                                                ? "#FFFFFF"
                                                                : Colours.primary
                                                        }
                                                    />

                                                    <Text
                                                        style={[
                                                            styles.cardText,
                                                            selected &&
                                                                styles.selectedCardText,
                                                        ]}
                                                    >
                                                        {
                                                            item.label
                                                        }
                                                    </Text>

                                                </TouchableOpacity>

                                            );

                                        }
                                    )}

                                </View>

                                <TextInput
                                    style={styles.input}
                                    placeholder="Additional information (optional)"
                                    placeholderTextColor={
                                        Colours.muted
                                    }
                                    multiline
                                    value={description}
                                    onChangeText={
                                        setDescription
                                    }
                                />

                                <Text
                                    style={
                                        styles.footnote
                                    }
                                >
                                    (Reports are always submitted using your current time.)
                                </Text>

                                <TouchableOpacity
                                    style={[
                                        styles.submitButton,
                                        (!issueType ||
                                            (mode ===
                                                "venue" &&
                                                !selectedVenue)) &&
                                            styles.disabledButton,
                                    ]}
                                    disabled={
                                        !issueType ||
                                        (mode ===
                                            "venue" &&
                                            !selectedVenue)
                                    }
                                    onPress={
                                        handleSubmit
                                    }
                                >

                                    <Ionicons
                                        name="warning"
                                        size={20}
                                        color="#FFFFFF"
                                    />

                                    <Text
                                        style={
                                            styles.submitText
                                        }
                                    >
                                        Submit Report
                                    </Text>

                                </TouchableOpacity>

                            </>

                        )}

                    </ScrollView>

                </View>
            </View>
        </Modal>
    );
}
const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        justifyContent: "flex-end",
        backgroundColor: "rgba(0,0,0,0.35)",
    },

    sheet: {
        backgroundColor: "#FFFFFF",
        borderTopLeftRadius: 28,
        borderTopRightRadius: 28,
        paddingHorizontal: 24,
        paddingTop: 18,
        paddingBottom: 32,
        maxHeight: "92%",
    },

    handle: {
        width: 48,
        height: 5,
        borderRadius: 999,
        backgroundColor: "#D1D5DB",
        alignSelf: "center",
        marginBottom: 20,
    },

    header: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 10,
    },

    title: {
        ...Typography.h2,
    },

    subtitle: {
        color: Colours.muted,
        fontSize: 15,
        lineHeight: 22,
        marginBottom: 22,
    },

    sectionTitle: {
        fontSize: 17,
        fontWeight: "700",
        color: Colours.text,
        marginBottom: 12,
        marginTop: 10,
    },

    modeContainer: {
        flexDirection: "row",
        justifyContent: "space-between",
        marginBottom: 24,
    },

    modeCard: {
        width: "48%",
        backgroundColor: Colours.surface,
        borderRadius: 18,
        paddingVertical: 20,
        paddingHorizontal: 12,
        alignItems: "center",
        justifyContent: "center",
        borderWidth: 2,
        borderColor: "transparent",
    },

    grid: {
        flexDirection: "row",
        flexWrap: "wrap",
        justifyContent: "space-between",
        marginBottom: 8,
    },

    card: {
        width: "48%",
        backgroundColor: Colours.surface,
        borderRadius: 16,
        paddingVertical: 18,
        paddingHorizontal: 12,
        alignItems: "center",
        justifyContent: "center",
        marginBottom: 12,
        borderWidth: 2,
        borderColor: "transparent",
    },

    selectedCard: {
        backgroundColor: Colours.primary,
        borderColor: Colours.primary,
    },

    cardText: {
        marginTop: 10,
        textAlign: "center",
        fontWeight: "600",
        fontSize: 14,
        color: Colours.text,
    },

    selectedCardText: {
        color: "#FFFFFF",
    },

    venueRow: {
        flexDirection: "row",
        justifyContent: "space-between",
        alignItems: "center",
        backgroundColor: Colours.surface,
        paddingHorizontal: 18,
        paddingVertical: 16,
        borderRadius: 16,
        marginBottom: 10,
        borderWidth: 2,
        borderColor: "transparent",
    },

    selectedVenue: {
        borderColor: Colours.primary,
        backgroundColor: "#FFF9E8",
    },

    venueName: {
        fontSize: 16,
        fontWeight: "700",
        color: Colours.text,
    },

    venueDistance: {
        marginTop: 4,
        fontSize: 13,
        color: Colours.muted,
    },

    input: {
        minHeight: 110,
        borderWidth: 1,
        borderColor: Colours.border,
        borderRadius: 16,
        paddingHorizontal: 16,
        paddingVertical: 14,
        marginTop: 12,
        color: Colours.text,
        textAlignVertical: "top",
        fontSize: 15,
        marginBottom: 10,
    },

    footnote: {
        textAlign: "center",
        fontSize: 12,
        color: Colours.muted,
        marginBottom: 18,
        fontStyle: "italic",
    },

    submitButton: {
        backgroundColor: Colours.primary,
        borderRadius: 18,
        paddingVertical: 17,
        alignItems: "center",
        justifyContent: "center",
        flexDirection: "row",
        marginTop: 6,
    },

    disabledButton: {
        opacity: 0.45,
    },

    submitText: {
        color: "#FFFFFF",
        fontWeight: "700",
        fontSize: 16,
        marginLeft: 8,
    },
});