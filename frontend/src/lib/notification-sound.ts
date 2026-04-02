export function playNotificationSound() {
  try {
    const ctx = new AudioContext();
    const freqs = [523, 659, 784]; // C5, E5, G5 — major chord ascending
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = freq;
      osc.type = "sine";
      gain.gain.value = 0.15;
      osc.start(ctx.currentTime + i * 0.15);
      gain.gain.exponentialRampToValueAtTime(
        0.001,
        ctx.currentTime + i * 0.15 + 0.3
      );
      osc.stop(ctx.currentTime + i * 0.15 + 0.3);
    });
  } catch {
    // Audio not available — ignore silently
  }
}
