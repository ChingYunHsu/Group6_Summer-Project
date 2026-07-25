export type AllergyKey =
  | "penicillin"
  | "amoxicillin"
  | "sulfa_drugs"
  | "aspirin"
  | "nsaids"
  | "latex"
  | "peanuts"
  | "tree_nuts"
  | "shellfish"
  | "fish"
  | "milk"
  | "eggs"
  | "soy"
  | "wheat_gluten"
  | "sesame"
  | "bee_stings"
  | "wasp_stings"
  | "contrast_dye"
  | "anesthesia"
  | "iodine"
  | "adhesive_tape"
  | "pollen"
  | "dust_mites"
  | "pet_dander"
  | "mold";

type AllergyTranslations = Record<
  "en" | "es" | "fr" | "it" | "de" | "zh",
  string
>;

export const allergies: Record<AllergyKey, AllergyTranslations> = {
  penicillin: {
    en: "Penicillin",
    es: "Penicilina",
    fr: "Pénicilline",
    it: "Penicillina",
    de: "Penicillin",
    zh: "青霉素",
  },
  amoxicillin: {
    en: "Amoxicillin",
    es: "Amoxicilina",
    fr: "Amoxicilline",
    it: "Amoxicillina",
    de: "Amoxicillin",
    zh: "阿莫西林",
  },
  sulfa_drugs: {
    en: "Sulfa Drugs",
    es: "Medicamentos con sulfa",
    fr: "Médicaments sulfamidés",
    it: "Farmaci sulfamidici",
    de: "Sulfonamide",
    zh: "磺胺类药物",
  },
  aspirin: {
    en: "Aspirin",
    es: "Aspirina",
    fr: "Aspirine",
    it: "Aspirina",
    de: "Aspirin",
    zh: "阿司匹林",
  },
  nsaids: {
    en: "NSAIDs (e.g. Ibuprofen)",
    es: "AINE (p. ej. Ibuprofeno)",
    fr: "AINS (ex. Ibuprofène)",
    it: "FANS (es. Ibuprofene)",
    de: "NSAR (z. B. Ibuprofen)",
    zh: "非甾体抗炎药（如布洛芬）",
  },
  latex: {
    en: "Latex",
    es: "Látex",
    fr: "Latex",
    it: "Lattice",
    de: "Latex",
    zh: "乳胶",
  },
  peanuts: {
    en: "Peanuts",
    es: "Cacahuetes",
    fr: "Arachides",
    it: "Arachidi",
    de: "Erdnüsse",
    zh: "花生",
  },
  tree_nuts: {
    en: "Tree Nuts",
    es: "Frutos secos",
    fr: "Fruits à coque",
    it: "Frutta a guscio",
    de: "Baumnüsse",
    zh: "坚果",
  },
  shellfish: {
    en: "Shellfish",
    es: "Mariscos",
    fr: "Fruits de mer",
    it: "Crostacei",
    de: "Schalentiere",
    zh: "贝类",
  },
  fish: {
    en: "Fish",
    es: "Pescado",
    fr: "Poisson",
    it: "Pesce",
    de: "Fisch",
    zh: "鱼类",
  },
  milk: {
    en: "Milk / Dairy",
    es: "Leche / Lácteos",
    fr: "Lait / Produits laitiers",
    it: "Latte / Latticini",
    de: "Milch / Milchprodukte",
    zh: "牛奶/乳制品",
  },
  eggs: {
    en: "Eggs",
    es: "Huevos",
    fr: "Œufs",
    it: "Uova",
    de: "Eier",
    zh: "鸡蛋",
  },
  soy: {
    en: "Soy",
    es: "Soja",
    fr: "Soja",
    it: "Soia",
    de: "Soja",
    zh: "大豆",
  },
  wheat_gluten: {
    en: "Wheat / Gluten",
    es: "Trigo / Gluten",
    fr: "Blé / Gluten",
    it: "Grano / Glutine",
    de: "Weizen / Gluten",
    zh: "小麦/麸质",
  },
  sesame: {
    en: "Sesame",
    es: "Sésamo",
    fr: "Sésame",
    it: "Sesamo",
    de: "Sesam",
    zh: "芝麻",
  },
  bee_stings: {
    en: "Bee Stings",
    es: "Picaduras de abeja",
    fr: "Piqûres d'abeille",
    it: "Punture d'ape",
    de: "Bienenstiche",
    zh: "蜜蜂蜇伤",
  },
  wasp_stings: {
    en: "Wasp Stings",
    es: "Picaduras de avispa",
    fr: "Piqûres de guêpe",
    it: "Punture di vespa",
    de: "Wespenstiche",
    zh: "黄蜂蜇伤",
  },
  contrast_dye: {
    en: "Contrast Dye",
    es: "Medio de contraste",
    fr: "Produit de contraste",
    it: "Mezzo di contrasto",
    de: "Kontrastmittel",
    zh: "造影剂",
  },
  anesthesia: {
    en: "Anesthesia",
    es: "Anestesia",
    fr: "Anesthésie",
    it: "Anestesia",
    de: "Anästhesie",
    zh: "麻醉药",
  },
  iodine: {
    en: "Iodine",
    es: "Yodo",
    fr: "Iode",
    it: "Iodio",
    de: "Jod",
    zh: "碘",
  },
  adhesive_tape: {
    en: "Adhesive Tape",
    es: "Cinta adhesiva",
    fr: "Ruban adhésif",
    it: "Nastro adesivo",
    de: "Klebeband",
    zh: "胶带",
  },
  pollen: {
    en: "Pollen",
    es: "Polen",
    fr: "Pollen",
    it: "Polline",
    de: "Pollen",
    zh: "花粉",
  },
  dust_mites: {
    en: "Dust Mites",
    es: "Ácaros del polvo",
    fr: "Acariens",
    it: "Acari della polvere",
    de: "Hausstaubmilben",
    zh: "尘螨",
  },
  pet_dander: {
    en: "Pet Dander",
    es: "Caspa de mascotas",
    fr: "Squames d'animaux",
    it: "Forfora di animali",
    de: "Tierhaare/-schuppen",
    zh: "宠物皮屑",
  },
  mold: {
    en: "Mold",
    es: "Moho",
    fr: "Moisissure",
    it: "Muffa",
    de: "Schimmel",
    zh: "霉菌",
  },
};

// Looks up an allergy's translated label for the given language code.
// Falls back to the raw key if it isn't in the curated list — the same
// safe passthrough free-text entries rely on, mirroring
// getConditionLabel in medicalConditions.ts.
export function getAllergyLabel(
  key: string,
  languageCode: keyof AllergyTranslations,
): string {
  const entry = allergies[key as AllergyKey];
  return entry ? entry[languageCode] : key;
}
