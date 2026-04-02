import { playNotificationSound } from "./notification-sound";

export function sendCaptchaNotification() {
  playNotificationSound();

  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;

  new Notification("Captcha detectado", {
    body: "Se requiere tu intervencion para resolver el captcha.",
    tag: "captcha-alert",
  });
}

export async function requestNotificationPermission() {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    await Notification.requestPermission();
  }
}
