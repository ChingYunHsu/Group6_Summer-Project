export const PROFILE_PHOTO_KEY = "clearpath_profile_photo";
export const PROFILE_GENDER_KEY = "clearpath_profile_gender";
export const PROFILE_AVATAR_EVENT =
  "clearpath:profile-avatar-updated";

export function getGenderEmoji(gender) {
  const normalisedGender = String(gender ?? "")
    .trim()
    .toLowerCase();

  if (
    normalisedGender === "female" ||
    normalisedGender === "woman" ||
    normalisedGender === "f"
  ) {
    return "👩";
  }

  if (
    normalisedGender === "male" ||
    normalisedGender === "man" ||
    normalisedGender === "m"
  ) {
    return "👨";
  }

  return "🧑";
}

export function notifyProfileAvatarUpdated() {
  window.dispatchEvent(new Event(PROFILE_AVATAR_EVENT));
}

/*
 * Resize and crop the selected image before placing it in localStorage.
 * This prevents a large original photo from exceeding browser storage.
 */
export function resizeProfilePhoto(file, size = 256) {
  return new Promise((resolve, reject) => {
    if (!file?.type?.startsWith("image/")) {
      reject(new Error("Please choose an image file."));
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    const image = new Image();

    image.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        const context = canvas.getContext("2d");

        if (!context) {
          throw new Error("Image processing is unavailable.");
        }

        canvas.width = size;
        canvas.height = size;

        const cropSize = Math.min(
          image.naturalWidth,
          image.naturalHeight
        );

        const sourceX =
          (image.naturalWidth - cropSize) / 2;
        const sourceY =
          (image.naturalHeight - cropSize) / 2;

        context.drawImage(
          image,
          sourceX,
          sourceY,
          cropSize,
          cropSize,
          0,
          0,
          size,
          size
        );

        resolve(canvas.toDataURL("image/jpeg", 0.82));
      } catch (error) {
        reject(error);
      } finally {
        URL.revokeObjectURL(objectUrl);
      }
    };

    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("The selected image could not be read."));
    };

    image.src = objectUrl;
  });
}