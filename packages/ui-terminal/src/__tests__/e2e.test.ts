import { spawn } from 'child_process'
import { EventEmitter } from 'events'

describe('E2E: Complete User Flow', () => {
  let process: ReturnType<typeof spawn>
  let output: string

  beforeEach(() => {
    output = ''
  })

  afterEach(() => {
    if (process) {
      process.kill()
    }
  })

  it('launches terminal UI successfully', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      expect(output).toContain('Lyra')
      done()
    }, 1000)
  })

  it('handles user input and response', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      process.stdin.write('Hello\n')
    }, 500)

    setTimeout(() => {
      expect(output).toContain('Hello')
      done()
    }, 2000)
  })

  it('displays status updates', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      expect(output).toMatch(/idle|thinking|streaming/)
      done()
    }, 1000)
  })

  it('handles graceful shutdown', (done) => {
    process = spawn('node', ['dist/index.js'])

    setTimeout(() => {
      process.stdin.write('\x03') // Ctrl+C
    }, 500)

    process.on('exit', (code) => {
      expect(code).toBe(0)
      done()
    })
  })

  it('handles multiple messages in sequence', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => process.stdin.write('First\n'), 500)
    setTimeout(() => process.stdin.write('Second\n'), 1000)
    setTimeout(() => process.stdin.write('Third\n'), 1500)

    setTimeout(() => {
      expect(output).toContain('First')
      expect(output).toContain('Second')
      expect(output).toContain('Third')
      done()
    }, 2500)
  })

  it('handles command history navigation', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => process.stdin.write('Command 1\n'), 500)
    setTimeout(() => process.stdin.write('Command 2\n'), 1000)
    setTimeout(() => process.stdin.write('\x1B[A'), 1500) // Up arrow

    setTimeout(() => {
      expect(output).toContain('Command 2')
      done()
    }, 2000)
  })

  it('handles long streaming response', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      process.stdin.write('Generate a long response\n')
    }, 500)

    setTimeout(() => {
      expect(output.length).toBeGreaterThan(100)
      done()
    }, 5000)
  })

  it('handles error recovery', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    process.stderr.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      // Trigger error condition
      process.stdin.write('INVALID_COMMAND\n')
    }, 500)

    setTimeout(() => {
      // Should recover and accept new input
      process.stdin.write('Valid command\n')
    }, 1500)

    setTimeout(() => {
      expect(output).toContain('Valid command')
      done()
    }, 2500)
  })

  it('handles rapid input', (done) => {
    process = spawn('node', ['dist/index.js'])

    process.stdout.on('data', (data) => {
      output += data.toString()
    })

    setTimeout(() => {
      for (let i = 0; i < 10; i++) {
        process.stdin.write(`Message ${i}\n`)
      }
    }, 500)

    setTimeout(() => {
      expect(output).toContain('Message 0')
      expect(output).toContain('Message 9')
      done()
    }, 3000)
  })

  it('maintains UI responsiveness under load', (done) => {
    process = spawn('node', ['dist/index.js'])

    let frameCount = 0
    process.stdout.on('data', () => {
      frameCount++
    })

    setTimeout(() => {
      expect(frameCount).toBeGreaterThan(10)
      done()
    }, 2000)
  })
})
