// This is a starting list, not exhaustive — the medical-id.tsx add-
// condition flow should always allow free text as a fallback for
// anything not covered here (see getConditionLabel below).

export type MedicalConditionKey =
  | "asthma"
  | "diabetes_type1"
  | "diabetes_type2"
  | "epilepsy"
  | "high_blood_pressure"
  | "heart_disease"
  | "copd"
  | "kidney_disease"
  | "liver_disease"
  | "cancer"
  | "hiv_aids"
  | "hepatitis_b"
  | "hepatitis_c"
  | "tuberculosis"
  | "arthritis"
  | "osteoporosis"
  | "depression"
  | "anxiety"
  | "bipolar_disorder"
  | "schizophrenia"
  | "dementia"
  | "alzheimers"
  | "parkinsons"
  | "multiple_sclerosis"
  | "stroke_history"
  | "blood_clotting_disorder"
  | "anemia"
  | "thyroid_disorder"
  | "celiac_disease"
  | "crohns_disease"
  | "ulcerative_colitis"
  | "irritable_bowel_syndrome"
  | "migraine"
  | "sleep_apnea"
  | "pacemaker"
  | "organ_transplant"
  | "pregnant"
  | "immunocompromised"
  | "down_syndrome"
  | "autism_spectrum_disorder"
  | "deaf_or_hard_of_hearing"
  | "blind_or_low_vision";

type ConditionTranslations = Record<
  "en" | "es" | "fr" | "it" | "de" | "zh",
  string
>;

export const medicalConditions: Record<
  MedicalConditionKey,
  ConditionTranslations
> = {
  asthma: {
    en: "Asthma",
    es: "Asma",
    fr: "Asthme",
    it: "Asma",
    de: "Asthma",
    zh: "哮喘",
  },
  diabetes_type1: {
    en: "Type 1 Diabetes",
    es: "Diabetes tipo 1",
    fr: "Diabète de type 1",
    it: "Diabete di tipo 1",
    de: "Diabetes Typ 1",
    zh: "1型糖尿病",
  },
  diabetes_type2: {
    en: "Type 2 Diabetes",
    es: "Diabetes tipo 2",
    fr: "Diabète de type 2",
    it: "Diabete di tipo 2",
    de: "Diabetes Typ 2",
    zh: "2型糖尿病",
  },
  epilepsy: {
    en: "Epilepsy",
    es: "Epilepsia",
    fr: "Épilepsie",
    it: "Epilessia",
    de: "Epilepsie",
    zh: "癫痫",
  },
  high_blood_pressure: {
    en: "High Blood Pressure",
    es: "Presión arterial alta",
    fr: "Hypertension artérielle",
    it: "Pressione alta",
    de: "Bluthochdruck",
    zh: "高血压",
  },
  heart_disease: {
    en: "Heart Disease",
    es: "Enfermedad cardíaca",
    fr: "Maladie cardiaque",
    it: "Malattia cardiaca",
    de: "Herzkrankheit",
    zh: "心脏病",
  },
  copd: {
    en: "COPD",
    es: "EPOC",
    fr: "BPCO",
    it: "BPCO",
    de: "COPD",
    zh: "慢性阻塞性肺病",
  },
  kidney_disease: {
    en: "Kidney Disease",
    es: "Enfermedad renal",
    fr: "Maladie rénale",
    it: "Malattia renale",
    de: "Nierenerkrankung",
    zh: "肾病",
  },
  liver_disease: {
    en: "Liver Disease",
    es: "Enfermedad hepática",
    fr: "Maladie du foie",
    it: "Malattia epatica",
    de: "Lebererkrankung",
    zh: "肝病",
  },
  cancer: {
    en: "Cancer",
    es: "Cáncer",
    fr: "Cancer",
    it: "Cancro",
    de: "Krebs",
    zh: "癌症",
  },
  hiv_aids: {
    en: "HIV/AIDS",
    es: "VIH/SIDA",
    fr: "VIH/SIDA",
    it: "HIV/AIDS",
    de: "HIV/AIDS",
    zh: "艾滋病",
  },
  hepatitis_b: {
    en: "Hepatitis B",
    es: "Hepatitis B",
    fr: "Hépatite B",
    it: "Epatite B",
    de: "Hepatitis B",
    zh: "乙型肝炎",
  },
  hepatitis_c: {
    en: "Hepatitis C",
    es: "Hepatitis C",
    fr: "Hépatite C",
    it: "Epatite C",
    de: "Hepatitis C",
    zh: "丙型肝炎",
  },
  tuberculosis: {
    en: "Tuberculosis",
    es: "Tuberculosis",
    fr: "Tuberculose",
    it: "Tubercolosi",
    de: "Tuberkulose",
    zh: "结核病",
  },
  arthritis: {
    en: "Arthritis",
    es: "Artritis",
    fr: "Arthrite",
    it: "Artrite",
    de: "Arthritis",
    zh: "关节炎",
  },
  osteoporosis: {
    en: "Osteoporosis",
    es: "Osteoporosis",
    fr: "Ostéoporose",
    it: "Osteoporosi",
    de: "Osteoporose",
    zh: "骨质疏松症",
  },
  depression: {
    en: "Depression",
    es: "Depresión",
    fr: "Dépression",
    it: "Depressione",
    de: "Depression",
    zh: "抑郁症",
  },
  anxiety: {
    en: "Anxiety Disorder",
    es: "Trastorno de ansiedad",
    fr: "Trouble anxieux",
    it: "Disturbo d'ansia",
    de: "Angststörung",
    zh: "焦虑症",
  },
  bipolar_disorder: {
    en: "Bipolar Disorder",
    es: "Trastorno bipolar",
    fr: "Trouble bipolaire",
    it: "Disturbo bipolare",
    de: "Bipolare Störung",
    zh: "双相情感障碍",
  },
  schizophrenia: {
    en: "Schizophrenia",
    es: "Esquizofrenia",
    fr: "Schizophrénie",
    it: "Schizofrenia",
    de: "Schizophrenie",
    zh: "精神分裂症",
  },
  dementia: {
    en: "Dementia",
    es: "Demencia",
    fr: "Démence",
    it: "Demenza",
    de: "Demenz",
    zh: "痴呆症",
  },
  alzheimers: {
    en: "Alzheimer's Disease",
    es: "Enfermedad de Alzheimer",
    fr: "Maladie d'Alzheimer",
    it: "Malattia di Alzheimer",
    de: "Alzheimer-Krankheit",
    zh: "阿尔茨海默病",
  },
  parkinsons: {
    en: "Parkinson's Disease",
    es: "Enfermedad de Parkinson",
    fr: "Maladie de Parkinson",
    it: "Malattia di Parkinson",
    de: "Parkinson-Krankheit",
    zh: "帕金森病",
  },
  multiple_sclerosis: {
    en: "Multiple Sclerosis",
    es: "Esclerosis múltiple",
    fr: "Sclérose en plaques",
    it: "Sclerosi multipla",
    de: "Multiple Sklerose",
    zh: "多发性硬化症",
  },
  stroke_history: {
    en: "History of Stroke",
    es: "Antecedente de accidente cerebrovascular",
    fr: "Antécédent d'AVC",
    it: "Storia di ictus",
    de: "Schlaganfall in der Vorgeschichte",
    zh: "中风病史",
  },
  blood_clotting_disorder: {
    en: "Blood Clotting Disorder",
    es: "Trastorno de coagulación",
    fr: "Trouble de la coagulation",
    it: "Disturbo della coagulazione",
    de: "Blutgerinnungsstörung",
    zh: "凝血障碍",
  },
  anemia: {
    en: "Anemia",
    es: "Anemia",
    fr: "Anémie",
    it: "Anemia",
    de: "Anämie",
    zh: "贫血",
  },
  thyroid_disorder: {
    en: "Thyroid Disorder",
    es: "Trastorno de tiroides",
    fr: "Trouble thyroïdien",
    it: "Disturbo tiroideo",
    de: "Schilddrüsenerkrankung",
    zh: "甲状腺疾病",
  },
  celiac_disease: {
    en: "Celiac Disease",
    es: "Enfermedad celíaca",
    fr: "Maladie cœliaque",
    it: "Celiachia",
    de: "Zöliakie",
    zh: "乳糜泻",
  },
  crohns_disease: {
    en: "Crohn's Disease",
    es: "Enfermedad de Crohn",
    fr: "Maladie de Crohn",
    it: "Morbo di Crohn",
    de: "Morbus Crohn",
    zh: "克罗恩病",
  },
  ulcerative_colitis: {
    en: "Ulcerative Colitis",
    es: "Colitis ulcerosa",
    fr: "Colite ulcéreuse",
    it: "Colite ulcerosa",
    de: "Colitis ulcerosa",
    zh: "溃疡性结肠炎",
  },
  irritable_bowel_syndrome: {
    en: "Irritable Bowel Syndrome",
    es: "Síndrome del intestino irritable",
    fr: "Syndrome de l'intestin irritable",
    it: "Sindrome dell'intestino irritabile",
    de: "Reizdarmsyndrom",
    zh: "肠易激综合症",
  },
  migraine: {
    en: "Migraine",
    es: "Migraña",
    fr: "Migraine",
    it: "Emicrania",
    de: "Migräne",
    zh: "偏头痛",
  },
  sleep_apnea: {
    en: "Sleep Apnea",
    es: "Apnea del sueño",
    fr: "Apnée du sommeil",
    it: "Apnea notturna",
    de: "Schlafapnoe",
    zh: "睡眠呼吸暂停",
  },
  pacemaker: {
    en: "Pacemaker",
    es: "Marcapasos",
    fr: "Stimulateur cardiaque",
    it: "Pacemaker",
    de: "Herzschrittmacher",
    zh: "心脏起搏器",
  },
  organ_transplant: {
    en: "Organ Transplant",
    es: "Trasplante de órgano",
    fr: "Greffe d'organe",
    it: "Trapianto d'organo",
    de: "Organtransplantation",
    zh: "器官移植",
  },
  pregnant: {
    en: "Pregnant",
    es: "Embarazada",
    fr: "Enceinte",
    it: "Incinta",
    de: "Schwanger",
    zh: "怀孕",
  },
  immunocompromised: {
    en: "Immunocompromised",
    es: "Inmunocomprometido",
    fr: "Immunodéprimé",
    it: "Immunocompromesso",
    de: "Immungeschwächt",
    zh: "免疫功能低下",
  },
  down_syndrome: {
    en: "Down Syndrome",
    es: "Síndrome de Down",
    fr: "Trisomie 21",
    it: "Sindrome di Down",
    de: "Down-Syndrom",
    zh: "唐氏综合症",
  },
  autism_spectrum_disorder: {
    en: "Autism Spectrum Disorder",
    es: "Trastorno del espectro autista",
    fr: "Trouble du spectre autistique",
    it: "Disturbo dello spettro autistico",
    de: "Autismus-Spektrum-Störung",
    zh: "自闭症谱系障碍",
  },
  deaf_or_hard_of_hearing: {
    en: "Deaf or Hard of Hearing",
    es: "Sordo o con dificultad auditiva",
    fr: "Sourd ou malentendant",
    it: "Sordo o ipoudente",
    de: "Gehörlos oder schwerhörig",
    zh: "失聪或听力障碍",
  },
  blind_or_low_vision: {
    en: "Blind or Low Vision",
    es: "Ciego o con baja visión",
    fr: "Aveugle ou malvoyant",
    it: "Cieco o ipovedente",
    de: "Blind oder sehbehindert",
    zh: "失明或视力低下",
  },
};

// Looks up a condition's translated label for the given language code.
// Falls back to the raw key if it isn't in the curated list at all —
// this is what makes free-text entries (anything typed that doesn't
// match a suggestion) safe to pass through here too.
export function getConditionLabel(
  key: string,
  languageCode: keyof ConditionTranslations,
): string {
  const entry = medicalConditions[key as MedicalConditionKey];
  return entry ? entry[languageCode] : key;
}
