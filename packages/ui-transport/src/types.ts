export interface TransportMessage {
  type: string
  content: string
  timestamp: number
  metadata?: Record<string, unknown>
}
