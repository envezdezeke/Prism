// Components import formatters from here only (UI_PLAYBOOK section 3).
export { fmtSimTime, fmtDuration } from '../time/timeview.ts'

const money = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

export function fmtMoney(n: number): string {
  return money.format(n)
}
