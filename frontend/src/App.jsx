import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'
import DaveChat from "./components/DaveChat";

const API_BASE = 'https://gridshield-backend.onrender.com'
const CRITICAL_LINES = [27, 15, 40, 29, 9]

function GridTopologySVG({ nodes, edges, cascadeSequence, activeLine }) {
  const size = 480
  const center = size / 2
  const radius = 190

  const nodePositions = nodes.map((n, i) => {
    const angle = (i / nodes.length) * 2 * Math.PI - Math.PI / 2
    return {
      id: n.id,
      x: center + radius * Math.cos(angle),
      y: center + radius * Math.sin(angle),
    }
  })

  const posById = Object.fromEntries(nodePositions.map(p => [p.id, p]))

  const isFailedEdge = (edge) => {
    if (!cascadeSequence) return false
    return cascadeSequence.includes(edge.lineIndex)
  }

  return (
    <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ maxHeight: 460 }}>
      {edges.map((e, i) => {
        const a = posById[e.source]
        const b = posById[e.target]
        if (!a || !b) return null
        const failed = isFailedEdge(e)
        return (
          <line
            key={i}
            x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke={failed ? 'var(--danger-red)' : 'rgba(62, 201, 214, 0.25)'}
            strokeWidth={failed ? 2.5 : 1}
            style={{ transition: 'all 0.4s ease' }}
          />
        )
      })}
      {nodePositions.map((p) => (
        <g key={p.id} style={{ transition: 'all 0.4s ease' }}>
          <circle
            cx={p.x} cy={p.y} r={p.id === activeLine ? 9 : 6}
            fill={p.id === activeLine ? 'var(--amber)' : 'var(--bg-panel-raised)'}
            stroke="var(--cyan)"
            strokeWidth="1.5"
          />
          <text
            x={p.x} y={p.y + 3.5}
            textAnchor="middle"
            fontSize="7"
            fontFamily="IBM Plex Mono, monospace"
            fill="var(--text-secondary)"
          >
            {p.id}
          </text>
        </g>
      ))}
    </svg>
  )
}

function App() {
  const [lineId, setLineId] = useState(27)
  const [topology, setTopology] = useState(null)
  const [cascadeResult, setCascadeResult] = useState(null)
  const [rerouteResult, setRerouteResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [whatIfNode, setWhatIfNode] = useState('')
  const [whatIfResult, setWhatIfResult] = useState(null)
  const [languages, setLanguages] = useState({})
  const [selectedLang, setSelectedLang] = useState('en')
  const [explanation, setExplanation] = useState(null)
  const [operatorNote, setOperatorNote] = useState('')
  const [explainLoading, setExplainLoading] = useState(false)
  const [recentRuns, setRecentRuns] = useState([])
  const [weather, setWeather] = useState(null)
  const [stressFactors, setStressFactors] = useState(null)
  const [backtestResult, setBacktestResult] = useState(null)
  const [backtestLoading, setBacktestLoading] = useState(false)

  useEffect(() => {
    axios.get(`${API_BASE}/grid-topology`)
      .then(res => {
        const edgesWithIndex = res.data.edges.map((e, i) => ({ ...e, lineIndex: i }))
        setTopology({ nodes: res.data.nodes, edges: edgesWithIndex })
      })
      .catch(() => setError('Cannot reach backend. Is uvicorn running on port 8000?'))
  }, [])

  useEffect(() => {
    axios.get(`${API_BASE}/languages`)
      .then(res => setLanguages(res.data))
      .catch(() => console.error('Could not load languages'))
  }, [])

  useEffect(() => {
    const fetchWeather = () => {
      axios.get(`${API_BASE}/weather`)
        .then(res => setWeather(res.data))
        .catch(() => console.error('Could not load weather'))
    }
    fetchWeather()
    const interval = setInterval(fetchWeather, 60000)
    return () => clearInterval(interval)
  }, [])

  const fetchHistory = async () => {
    try {
      const res = await axios.get(`${API_BASE}/history?limit=10`)
      setRecentRuns(res.data)
    } catch (err) {
      console.error('Could not load history')
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchStressFactors = async (id = lineId) => {
    try {
      const res = await axios.get(`${API_BASE}/stress-factors/${id}`)
      setStressFactors(res.data)
    } catch (err) {
      console.error('Could not load stress factors')
    }
  }

  const runBacktest = async (id = lineId) => {
    setBacktestLoading(true)
    setBacktestResult(null)
    try {
      const res = await axios.get(`${API_BASE}/backtest/${id}`)
      setBacktestResult(res.data)
    } catch (err) {
      console.error('Backtest failed')
    } finally {
      setBacktestLoading(false)
    }
  }

  const runAnalysis = async (id = lineId) => {
    setLoading(true)
    setError(null)
    setCascadeResult(null)
    setRerouteResult(null)
    setExplanation(null)
    try {
      const [cascadeRes, rerouteRes] = await Promise.all([
        axios.get(`${API_BASE}/simulate-cascade/${id}`),
        axios.get(`${API_BASE}/reroute/${id}`),
      ])
      setCascadeResult(cascadeRes.data)
      setRerouteResult(rerouteRes.data)
      fetchHistory()
      fetchStressFactors(id)
    } catch (err) {
      setError('Analysis failed. Check that the backend is running and the line ID is valid (0-40).')
    } finally {
      setLoading(false)
    }
  }

  const runExplain = async () => {
    setExplainLoading(true)
    setExplanation(null)
    try {
      const res = await axios.post(`${API_BASE}/explain`, {
        line_id: lineId,
        language: selectedLang,
        operator_note: operatorNote || null,
      })
      setExplanation(res.data.explanation)
    } catch (err) {
      setError('Explanation generation failed. Check backend and Groq API key.')
    } finally {
      setExplainLoading(false)
    }
  }

  const runWhatIf = async () => {
    if (whatIfNode === '') return
    setLoading(true)
    setError(null)
    try {
      const res = await axios.post(`${API_BASE}/what-if`, { line_id: Number(whatIfNode) })
      setWhatIfResult(res.data)
    } catch (err) {
      setError('What-if query failed. Enter a valid line ID (0-40).')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <div className="header-row">
        <div className="brand-mark">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="pulse-dot" />
              <h1 className="brand-title">GRID<span className="accent">SHIELD</span></h1>
            </div>
            <div className="brand-subtitle">Autonomous Resilience &amp; Rerouting Console</div>
          </div>
        </div>
        <div className="system-status">
          TOPOLOGY <span className="status-value">IEEE 30-BUS</span><br />
          NODES 30 &nbsp;·&nbsp; LINES 41<br />
          {weather?.temp_c != null && (
            <>🌡 {weather.temp_c}°C — {weather.city} <span style={{ color: 'var(--text-secondary)' }}>(live, 15-min poll)</span></>
          )}
        </div>
      </div>

      {error && <div className="error-banner">⚠ {error}</div>}

      <div className="grid-layout">
        <div className="panel">
          <p className="panel-label">Live Topology</p>
          <div className="grid-svg-wrap">
            {topology ? (
              <GridTopologySVG
                nodes={topology.nodes}
                edges={topology.edges}
                cascadeSequence={cascadeResult?.cascade_sequence}
                activeLine={lineId}
              />
            ) : (
              <div className="empty-state">Loading topology...</div>
            )}
          </div>
        </div>

        <div>
          <div className="panel">
            <p className="panel-label">Simulate Contingency</p>

            <div className="quick-picks">
              {CRITICAL_LINES.map(id => (
                <button key={id} className="quick-pick-chip" onClick={() => { setLineId(id); runAnalysis(id) }}>
                  LINE {id}
                </button>
              ))}
            </div>

            <div className="control-row">
              <input
                type="number" min="0" max="40" value={lineId}
                onChange={(e) => setLineId(Number(e.target.value))}
                className="line-input"
              />
              <button className="run-button" onClick={() => runAnalysis()} disabled={loading}>
                {loading ? 'Simulating...' : 'Run Contingency'}
              </button>
            </div>

            {!cascadeResult && !loading && (
              <div className="empty-state">Select a line and run analysis to see cascade + rerouting results</div>
            )}

            {cascadeResult && (
              <div className="result-card danger">
                <p className="result-title danger-text">⚠ Cascade If Unaddressed</p>
                <div className="metric-grid">
                  <div className="metric">
                    <div className="metric-value">{cascadeResult.total_failed_lines}</div>
                    <div className="metric-label">Lines Failed</div>
                  </div>
                </div>
                <div className="cascade-flow">
                  {cascadeResult.cascade_sequence.map((l, i) => (
                    <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span className="cascade-node">L{l}</span>
                      {i < cascadeResult.cascade_sequence.length - 1 && <span className="cascade-arrow">→</span>}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {rerouteResult && (
              <div className="result-card success">
                <p className="result-title success-text">✓ AI Rerouting Plan</p>
                <div className="metric-grid">
                  <div className="metric">
                    <div className="metric-value" style={{ color: 'var(--danger-red)' }}>
                      {rerouteResult.without_rerouting.max_loading_pct?.toFixed(0)}%
                    </div>
                    <div className="metric-label">Without Reroute</div>
                  </div>
                  <div className="metric">
                    <div className="metric-value" style={{ color: 'var(--safe-green)' }}>
                      {rerouteResult.with_rerouting.max_loading_pct?.toFixed(0) ?? '—'}%
                    </div>
                    <div className="metric-label">With Reroute</div>
                  </div>
                  <div className="metric">
                    <div className="metric-value" style={{ color: 'var(--cyan)' }}>
                      {rerouteResult.with_rerouting.status === 'REROUTED_SAFE' ? 'SAFE' : 'INFEASIBLE'}
                    </div>
                    <div className="metric-label">Final Status</div>
                  </div>
                </div>
              </div>
            )}

            {rerouteResult && (
              <div style={{ marginTop: '1.25rem' }}>
                <div className="control-row">
                  <select
                    value={selectedLang}
                    onChange={(e) => setSelectedLang(e.target.value)}
                    className="line-input"
                    style={{ width: '140px', textAlign: 'left', paddingLeft: '0.6rem' }}
                  >
                    {Object.entries(languages).map(([code, name]) => (
                      <option key={code} value={code}>{name}</option>
                    ))}
                  </select>
                  <button className="run-button" onClick={runExplain} disabled={explainLoading}>
                    {explainLoading ? 'Explaining...' : '💬 Explain This'}
                  </button>
                </div>

                {explanation && (
                  <div className="result-card" style={{ borderColor: 'var(--cyan)', marginTop: '0.75rem' }}>
                    <p className="result-title" style={{ color: 'var(--cyan)' }}>◆ AI Explanation</p>
                    <p style={{ fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-primary)' }}>
                      {explanation}
                    </p>
                  </div>
                )}

                <textarea
                  placeholder="Add your own note about this decision..."
                  value={operatorNote}
                  onChange={(e) => setOperatorNote(e.target.value)}
                  style={{
                    width: '100%', marginTop: '0.75rem', padding: '0.6rem',
                    background: 'var(--bg-panel-raised)', border: '1px solid var(--border-subtle)',
                    borderRadius: '4px', color: 'var(--text-primary)', fontFamily: 'IBM Plex Mono, monospace',
                    fontSize: '0.8rem', minHeight: '60px', resize: 'vertical', boxSizing: 'border-box'
                  }}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: '1.5rem' }}>
        <p className="panel-label">What-If Simulator</p>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '-0.5rem', marginBottom: '1rem' }}>
          Ask a hypothetical: "what happens if line X fails right now?"
        </p>
        <div className="control-row">
          <input
            type="number" min="0" max="40" placeholder="Line #"
            value={whatIfNode}
            onChange={(e) => setWhatIfNode(e.target.value)}
            className="line-input"
          />
          <button className="run-button" onClick={runWhatIf} disabled={loading}>
            Ask What-If
          </button>
        </div>

        {whatIfResult && (
          <div className="result-card" style={{ borderColor: 'var(--amber)' }}>
            <p className="result-title" style={{ color: 'var(--amber)' }}>
              ◆ Hypothetical: Line {whatIfResult.line_id} Fails Now
            </p>
            <div className="metric-grid">
              <div className="metric">
                <div className="metric-value">{whatIfResult.cascade_if_unaddressed.total_failed_lines}</div>
                <div className="metric-label">Would Cascade To</div>
              </div>
              <div className="metric">
                <div className="metric-value" style={{ color: whatIfResult.with_rerouting.status === 'REROUTED_SAFE' ? 'var(--safe-green)' : 'var(--danger-red)' }}>
                  {whatIfResult.with_rerouting.status === 'REROUTED_SAFE' ? 'FIXABLE' : 'CRITICAL'}
                </div>
                <div className="metric-label">Rerouting Outcome</div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginTop: '1.5rem' }}>
        <p className="panel-label">Live Stress Factors &amp; Historical Validation</p>

        {stressFactors && (
          <div className="metric-grid" style={{ marginBottom: '1rem' }}>
            <div className="metric">
              <div className="metric-value">{stressFactors.current_temp_c?.toFixed(1)}°C</div>
              <div className="metric-label">Live Temp</div>
            </div>
            <div className="metric">
              <div className="metric-value" style={{ color: 'var(--amber)' }}>
                {stressFactors.combined_stress_multiplier}x
              </div>
              <div className="metric-label">Stress Multiplier</div>
            </div>
            <div className="metric">
              <div className="metric-value">{stressFactors.ev_charging_factor}x</div>
              <div className="metric-label">EV Load Factor</div>
            </div>
            <div className="metric">
              <div className="metric-value">{stressFactors.solar_variability_factor}x</div>
              <div className="metric-label">Solar Factor</div>
            </div>
          </div>
        )}

        <button className="run-button" onClick={() => runBacktest()} disabled={backtestLoading} style={{ width: '100%' }}>
          {backtestLoading ? 'Comparing...' : '📊 Validate Against 2012 India Blackout Case Study'}
        </button>

        {backtestResult && (
          <div className="result-card" style={{ borderColor: 'var(--cyan)', marginTop: '0.9rem' }}>
            <p className="result-title" style={{ color: 'var(--cyan)' }}>◆ Historical Mechanism Comparison</p>
            <div className="metric-grid" style={{ marginBottom: '0.75rem' }}>
              <div className="metric">
                <div className="metric-value" style={{ color: backtestResult.mechanism_match.multi_stage_cascade ? 'var(--safe-green)' : 'var(--text-secondary)' }}>
                  {backtestResult.mechanism_match.multi_stage_cascade ? 'YES' : 'NO'}
                </div>
                <div className="metric-label">Multi-Stage Cascade</div>
              </div>
              <div className="metric">
                <div className="metric-value" style={{ color: backtestResult.mechanism_match.non_contiguous_pattern ? 'var(--safe-green)' : 'var(--text-secondary)' }}>
                  {backtestResult.mechanism_match.non_contiguous_pattern ? 'YES' : 'NO'}
                </div>
                <div className="metric-label">Non-Contiguous Pattern</div>
              </div>
            </div>
            <p style={{ fontSize: '0.82rem', lineHeight: '1.5', color: 'var(--text-primary)' }}>
              {backtestResult.mechanism_match.conclusion}
            </p>
          </div>
        )}
      </div>

      <div className="panel" style={{ marginTop: '1.5rem' }}>
        <p className="panel-label">Recent Activity (Database Log)</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {recentRuns.length === 0 && (
            <div className="empty-state">No runs logged yet</div>
          )}
          {recentRuns.map((run) => (
            <div key={run.id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '0.6rem 0.9rem', background: 'var(--bg-panel-raised)',
              borderRadius: '4px', fontFamily: 'IBM Plex Mono, monospace', fontSize: '0.78rem'
            }}>
              <span>Line {run.line_id}</span>
              <span style={{ color: 'var(--text-secondary)' }}>{run.total_failed_lines} lines cascaded</span>
              <span style={{ color: run.with_reroute_status === 'REROUTED_SAFE' ? 'var(--safe-green)' : 'var(--danger-red)' }}>
                {run.with_reroute_status === 'REROUTED_SAFE' ? 'FIXED' : 'CRITICAL'}
              </span>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.7rem' }}>
                {new Date(run.created_at).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>

      <DaveChat />
    </div>
  )
}

export default App