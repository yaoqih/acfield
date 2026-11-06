// Local elapsed times always use performance.now(); only this mapping yields server UTC.
export class ServerClock {
  private valid = false
  private offset = 0
  private target = 0
  private updated = 0
  private observed = 0
  private bestAt = 0
  private bestRtt = Infinity

  observe(t1: number, t2: number, t3: number, t4: number) {
    if (![t1, t2, t3, t4].every(Number.isFinite) || t4 < t1 || t3 < t2) return false
    const delay = (t4-t1)-(t3-t2)
    // Epoch milliseconds have coarser floating-point resolution than performance.now().
    if (delay < -.1 || delay > 40) return false
    const rtt = Math.max(0, delay)
    if (!this.valid || t4-this.bestAt > 10000 || rtt <= this.bestRtt+1) {
      const candidate = ((t2-t1)+(t3-t4))/2
      if (!this.valid) { this.offset = candidate; this.updated = t4 }
      else this.now(t4)
      this.target = candidate
      this.bestRtt = rtt; this.bestAt = this.observed = t4
      this.valid = true
    }
    return true
  }
  now(mono: number) {
    const limit = Math.max(0, mono-this.updated)*.001
    this.offset += Math.max(-limit, Math.min(limit, this.target-this.offset))
    this.updated = mono
    return mono+this.offset
  }
  ready(mono: number) {
    return this.valid && mono-this.observed < 15000 &&
      this.bestRtt/2+Math.abs(this.target-this.offset)+(mono-this.observed)*.0001 <= 20
  }
}
