import { useState, useEffect, useRef } from 'react';
import { Home, FileText, Upload, Settings, Users, LogOut, CheckCircle, Clock, BookOpen, BarChart3, Brain, ClipboardList, BookMarked, Trash2, Download, GitCompare } from 'lucide-react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, BarChart, Bar, CartesianGrid } from 'recharts';
import './index.css';

const API_BASE = 'http://localhost:8000/api';
const COLORS = ['#10b981', '#2dd4bf', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444'];

function App() {
  const [activeTab, setActiveTab] = useState('Dashboard');
  const [user, setUser] = useState(null);
  const [evaluatingIds, setEvaluatingIds] = useState(new Set());
  const [timers, setTimers] = useState({});
  
  if (!user) return <Login onLogin={setUser} />;

  return (
    <>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} user={user} onLogout={() => setUser(null)} />
      <main style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        {activeTab === 'Dashboard' && <Dashboard />}
        {activeTab === 'Upload Answers' && <UploadZone evaluatingIds={evaluatingIds} setEvaluatingIds={setEvaluatingIds} timers={timers} setTimers={setTimers} />}
        {activeTab === 'AI Evaluation' && <UploadZone evaluatingIds={evaluatingIds} setEvaluatingIds={setEvaluatingIds} timers={timers} setTimers={setTimers} showUpload={false} />}
        {activeTab === 'Results' && <ResultsView />}
        {activeTab === 'Analytics' && <AnalyticsView />}
        {activeTab === 'Model Comparison' && <ModelComparisonView />}
        {activeTab === 'AI Insights' && <AiInsightsView />}
        {activeTab === 'Settings' && <SettingsView />}
        {['Exam Management', 'Question Bank', 'Students', 'Courses'].includes(activeTab) && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60vh', color: 'var(--text-muted)' }}>
             <Settings size={48} style={{ opacity: 0.5, marginBottom: '20px' }} />
             <h2 className="title" style={{ fontSize: '1.5rem', marginBottom: '10px' }}>{activeTab}</h2>
             <p>This module is currently under construction and will be available soon.</p>
          </div>
        )}
      </main>
    </>
  );
}

function Sidebar({ activeTab, setActiveTab, user, onLogout }) {
  const sections = [
    {
      title: 'MAIN',
      items: [
        { id: 'Dashboard', icon: Home },
        { id: 'Exam Management', icon: ClipboardList },
        { id: 'Question Bank', icon: BookMarked }
      ]
    },
    {
      title: 'EVALUATION',
      items: [
        { id: 'Upload Answers', icon: Upload },
        { id: 'AI Evaluation', icon: Brain },
        { id: 'Results', icon: FileText }
      ]
    },
    {
      title: 'PEOPLE',
      items: [
        { id: 'Students', icon: Users },
        { id: 'Courses', icon: BookOpen }
      ]
    },
    {
      title: 'INSIGHTS',
      items: [
        { id: 'Analytics', icon: BarChart3 },
        { id: 'Model Comparison', icon: GitCompare },
        { id: 'AI Insights', icon: Brain },
        { id: 'Settings', icon: Settings }
      ]
    }
  ];

  return (
    <div className="glass-panel" style={{ width: '280px', margin: '20px', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
      <div style={{ padding: '30px 20px', borderBottom: '1px solid var(--glass-border)' }}>
        <h2 style={{ background: 'linear-gradient(to right, #60a5fa, #c084fc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: 0 }}>
          EvalAI
        </h2>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Automated Grading</div>
      </div>
      
      <div style={{ padding: '15px 20px', flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {sections.map(sec => (
          <div key={sec.title}>
            <div style={{ color: '#666', fontSize: '11px', fontWeight: 'bold', letterSpacing: '1px', marginBottom: '8px', paddingLeft: '10px' }}>
              {sec.title}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {sec.items.map(t => (
                <button 
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  style={{
                    background: activeTab === t.id ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                    color: activeTab === t.id ? 'var(--accent-hover)' : 'var(--text-muted)',
                    border: activeTab === t.id ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
                    padding: '10px 16px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '12px',
                    fontFamily: 'inherit', fontSize: '14px', fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s', width: '100%', textAlign: 'left'
                  }}
                >
                  <t.icon size={18} />
                  {t.id}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: '20px', borderTop: '1px solid var(--glass-border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <div style={{ width: '40px', height: '40px', borderRadius: '20px', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
            {user.name[0]}
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>{user.name}</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{user.email}</div>
          </div>
        </div>
        <button className="btn btn-ghost w-full" onClick={onLogout}>
          <LogOut size={16} /> Logout
        </button>
      </div>
    </div>
  );
}

function Login({ onLogin }) {
  const [email, setEmail] = useState('admin');
  const [password, setPassword] = useState('admin');

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post(`${API_BASE}/login`, { email, password });
      onLogin(res.data.user);
    } catch (e) {
      alert("Login failed");
    }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', width: '100%' }}>
      <div className="glass-panel animate-fade-in" style={{ width: '400px', padding: '40px' }}>
        <h2 className="title" style={{ textAlign: 'center' }}>EvalAI Sign In</h2>
        <form onSubmit={handleLogin}>
          <div className="input-container">
            <label>Email</label>
            <input type="text" value={email} onChange={e => setEmail(e.target.value)} />
          </div>
          <div className="input-container">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} />
          </div>
          <button type="submit" className="btn w-full mt-4">Sign In</button>
        </form>
      </div>
    </div>
  );
}

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [top, setTop] = useState([]);

  useEffect(() => {
    axios.get(`${API_BASE}/dashboard/stats`).then(r => setStats(r.data));
    axios.get(`${API_BASE}/analytics/top`).then(r => setTop(r.data));
  }, []);

  const s = stats || {};
  const avgScore = s.avg_score ?? 0;
  const passRate = s.pass_rate ?? 0;

  return (
    <div className="animate-fade-in">
      
      {/* Stat Cards Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '14px', marginBottom: '24px' }}>
        {[
          { label: 'Students', val: s.total_students ?? 0, color: '#3b82f6' },
          { label: 'Evaluated', val: s.evals_done ?? 0, color: '#10b981' },
          { label: 'Pending', val: s.evals_pending ?? 0, color: '#f59e0b' },
          { label: 'Avg Score', val: `${avgScore}%`, color: '#8b5cf6' },
          { label: 'Pass Rate', val: `${passRate}%`, color: passRate >= 60 ? '#10b981' : '#ef4444' },
        ].map(c => (
          <div key={c.label} className="glass-card">
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '1.2px', marginBottom: '10px' }}>
              {c.label}
            </div>
            <div style={{ fontSize: '26px', fontWeight: 800, color: c.color, lineHeight: 1 }}>
              {c.val}
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
        
        {/* Recent Evaluations */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <h4 style={{ marginBottom: '16px', color: 'white', fontWeight: 600, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={15} color="#60a5fa"/> Recent Evaluations
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {(s.recent?.length > 0) ? s.recent.map((r, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)' }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '13px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{r.student_name || 'Unknown'}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {[r.course_name, r.exam_type, r.division ? `Div ${r.division}` : null].filter(Boolean).join(' · ')}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexShrink: 0 }}>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 500 }}>{r.total_score}/{r.max_marks}</span>
                  <span className="badge" style={{ 
                    background: r.grade === 'F' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)', 
                    color: r.grade === 'F' ? '#ef4444' : '#10b981',
                    padding: '3px 8px', fontSize: '11px'
                  }}>{r.grade}</span>
                </div>
              </div>
            )) : (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '50px 20px', fontSize: '13px' }}>
                <FileText size={32} style={{ opacity: 0.2, margin: '0 auto 12px auto', display: 'block' }}/>
                No evaluations yet
              </div>
            )}
          </div>
        </div>

        {/* Right Column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Course Performance */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <h4 style={{ marginBottom: '16px', color: 'white', fontWeight: 600, fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={15} color="#8b5cf6"/> Course Performance
            </h4>
            {(s.course_stats?.length > 0) ? s.course_stats.map((cs, i) => (
              <div key={i} style={{ marginBottom: i < s.course_stats.length - 1 ? '14px' : 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px', alignItems: 'baseline' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600 }}>{cs.name}</span>
                  <span style={{ fontSize: '12px', color: cs.avg_pct >= 60 ? '#10b981' : '#f59e0b', fontWeight: 600 }}>{cs.avg_pct}% · {cs.count} evals</span>
                </div>
                <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.06)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(cs.avg_pct, 100)}%`, height: '100%', background: cs.avg_pct >= 70 ? 'linear-gradient(90deg, #10b981, #34d399)' : cs.avg_pct >= 40 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #ef4444, #f87171)', borderRadius: '3px', transition: 'width 0.8s ease' }} />
                </div>
              </div>
            )) : (
              <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0', fontSize: '13px' }}>
                <BarChart3 size={28} style={{ opacity: 0.2, margin: '0 auto 10px auto', display: 'block' }}/>
                No course data yet
              </div>
            )}
          </div>

          {/* Top Performers */}
          <div className="glass-panel" style={{ padding: '22px' }}>
            <h4 style={{ marginBottom: '16px', color: 'white', fontWeight: 600, fontSize: '14px' }}>
              🏆 Top Performers
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {top.length > 0 ? top.map((t, i) => (
                <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.04)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '18px', lineHeight: 1 }}>{i===0?'🥇':i===1?'🥈':'🥉'}</span>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '13px' }}>{t.name}</div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{t.exam_type || 'ISA-1'} · Div {t.division || 'A'}</div>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <span className="badge badge-success" style={{ padding: '3px 8px', fontSize: '11px' }}>{t.grade}</span>
                    <span style={{ color: 'var(--accent)', fontWeight: 700, fontSize: '14px' }}>{Number(t.pct).toFixed(1)}%</span>
                  </div>
                </div>
              )) : (
                <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px 0', fontSize: '13px' }}>
                  <Users size={28} style={{ opacity: 0.2, margin: '0 auto 10px auto', display: 'block' }}/>
                  No ranked students yet
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function UploadZone({ evaluatingIds, setEvaluatingIds, timers, setTimers, showUpload = true }) {
  const [rubric, setRubric] = useState(JSON.stringify({
    "questions": [
      {"q_no": "1", "max_marks": 10, "topic": "e.g. Neural Networks", "expected_keywords": "backpropagation, gradient descent"},
      {"q_no": "2", "max_marks": 10, "topic": "", "expected_keywords": ""}
    ]
  }, null, 2));
  const [file, setFile] = useState(null);
  const [filePreview, setFilePreview] = useState(null);
  const [student, setStudent] = useState({ name: '', id: '', roll: '' });
  const [division, setDivision] = useState('A');
  const [examType, setExamType] = useState('ISA-1');
  const [courseName, setCourseName] = useState('GenAI');
  const [marks, setMarks] = useState({ total: 100, pass: 40 });
  const [exams, setExams] = useState([]);
  const [examId, setExamId] = useState(1);
  const [pending, setPending] = useState([]);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [evalSuccess, setEvalSuccess] = useState(null);

  const fetchPending = async () => {
    try {
      const res = await axios.get(`${API_BASE}/evaluations/pending`);
      setPending(res.data);
    } catch { }
  };

  useEffect(() => {
    if (!file) {
      setFilePreview(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setFilePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => { 
    fetchPending(); 
    axios.get(`${API_BASE}/exams`).then(r => {
      if(r.data.length > 0) {
        setExams(r.data);
        setExamId(r.data[0].id);
      }
    });
  }, []);

  const handleUpload = async () => {
    if(!file) return alert("Select file");
    const formData = new FormData();
    formData.append('exam_id', examId);
    formData.append('rubrics_json', rubric);
    formData.append('total_marks', marks.total);
    formData.append('pass_marks', marks.pass);
    formData.append('student_name', student.name);
    formData.append('student_id', student.id);
    formData.append('roll_no', student.roll);
    formData.append('division', division);
    formData.append('exam_type', examType);
    formData.append('course_name', courseName);
    formData.append('file', file);

    try {
      await axios.post(`${API_BASE}/evaluations/upload`, formData);
      fetchPending();
      setFile(null);
      setUploadSuccess(true);
      setTimeout(() => setUploadSuccess(false), 4000);
    } catch (e) {
      console.log(e);
    }
  };

  const formatTime = (totalSeconds) => {
      if (totalSeconds < 60) return `${totalSeconds}s`;
      const m = Math.floor(totalSeconds / 60);
      const s = totalSeconds % 60;
      return `${m}m ${s}s`;
  };

  const handleEvaluateAll = async () => {
    const queue = [...pending];
    for (const p of queue) {
      await handleEvaluate(p.id);
    }
  };

  const handleEvaluate = async (subId) => {
    setEvaluatingIds(prev => new Set(prev).add(subId));
    
    const startTime = Date.now();
    const interval = setInterval(() => {
        setTimers(prev => ({...prev, [subId]: Math.floor((Date.now() - startTime) / 1000)}));
    }, 1000);

    try {
      await axios.post(`${API_BASE}/evaluations/run/${subId}`);
      fetchPending();
      setEvalSuccess("Evaluation successfully completed!");
      setTimeout(() => setEvalSuccess(null), 5000);
    } catch (e) {
      alert("Evaluation failed");
    } finally {
      clearInterval(interval);
      setEvaluatingIds(prev => {
        const next = new Set(prev);
        next.delete(subId);
        return next;
      });
      setTimers(prev => {
        const next = {...prev};
        delete next[subId];
        return next;
      });
    }
  };

  return (
    <div className="animate-fade-in" style={{ display: 'flex', gap: '30px', justifyContent: showUpload ? 'flex-start' : 'center' }}>
      {showUpload && (
      <div style={{ flex: 1, maxWidth: '600px' }}>
        
        <div className="glass-panel" style={{ padding: '25px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          <div style={{ padding: '20px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
            <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: 'var(--accent)', letterSpacing: '1px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BookOpen size={15}/> Exam Details
            </h4>
            <div style={{ display: 'flex', gap: '15px', marginBottom: '15px' }}>
              <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
                <label>Division</label>
                <select value={division} onChange={e=>setDivision(e.target.value)} style={{ padding: '12px', borderRadius: '8px', width: '100%' }}>
                  {['A', 'B', 'C', 'D', 'E'].map(d => <option key={d} value={d} style={{color: 'black'}}>Div {d}</option>)}
                </select>
              </div>
              <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
                <label>Exam Type</label>
                <select value={examType} onChange={e=>setExamType(e.target.value)} style={{ padding: '12px', borderRadius: '8px', width: '100%' }}>
                  {['ISA-1', 'ISA-2', 'ESA'].map(t => <option key={t} value={t} style={{color: 'black'}}>{t}</option>)}
                </select>
              </div>
              <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
                <label>Course</label>
                <select value={courseName} onChange={e=>setCourseName(e.target.value)} style={{ padding: '12px', borderRadius: '8px', width: '100%' }}>
                  {['GenAI', 'Cloud Computing'].map(c => <option key={c} value={c} style={{color: 'black'}}>{c}</option>)}
                </select>
              </div>
            </div>
            <div className="input-container" style={{ marginBottom: 0 }}>
              <label>Rubric & Answer Key (JSON)</label>
              <textarea rows={8} value={rubric} onChange={e=>setRubric(e.target.value)} style={{ padding: '12px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '12px', lineHeight: '1.5' }} />
              <p style={{ margin: '8px 0 0 0', fontSize: '11px', color: 'var(--text-muted)' }}>💡 Fill in <strong>topic</strong> and <strong>expected_keywords</strong> for each question to improve AI grading accuracy.</p>
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '20px' }}>
            <div style={{ flex: 1, padding: '20px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: '#10b981', letterSpacing: '1px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Users size={15}/> Student
              </h4>
              <div className="input-container" style={{ marginBottom: '15px' }}>
                <label>Student Name</label>
                <input value={student.name} onChange={e=>setStudent({...student, name: e.target.value})} placeholder="e.g. John Doe" />
              </div>
              <div className="input-container" style={{ marginBottom: 0 }}>
                <label>Student ID</label>
                <input value={student.id} onChange={e=>setStudent({...student, id: e.target.value})} placeholder="e.g. 12345" />
              </div>
            </div>
          
            <div style={{ flex: 1, padding: '20px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
              <h4 style={{ fontSize: '12px', textTransform: 'uppercase', color: '#f59e0b', letterSpacing: '1px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <BarChart3 size={15}/> Scoring
              </h4>
              <div className="input-container" style={{ marginBottom: '15px' }}>
                <label>Total Marks</label>
                <input type="number" value={marks.total} onChange={e=>setMarks({...marks, total: e.target.value})} />
              </div>
              <div className="input-container" style={{ marginBottom: 0 }}>
                <label>Passing Marks</label>
                <input type="number" value={marks.pass} onChange={e=>setMarks({...marks, pass: e.target.value})} />
              </div>
            </div>
          </div>

          <div style={{ padding: '20px', background: 'rgba(59, 130, 246, 0.05)', borderRadius: '12px', border: '1.5px dashed rgba(59, 130, 246, 0.4)', textAlign: 'center', transition: 'all 0.2s' }}>
            {!file ? (
              <label style={{ cursor: 'pointer', display: 'block' }}>
                <FileText size={32} color="var(--primary)" style={{ margin: '0 auto 10px auto', opacity: 0.8 }} />
                <div style={{ color: 'white', fontWeight: 600, textAlign: 'center', fontSize: '15px' }}>Attach Answer Script</div>
                <input type="file" accept="image/*,application/pdf" onChange={e => setFile(e.target.files[0])} style={{ display: 'none' }} />
                <div style={{ color: '#94a3b8', fontSize: '13px', marginTop: '5px' }}>Click or drag a PDF/Image here</div>
              </label>
            ) : (
              <div>
                 <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileText size={16}/> {file.name}
                    </div>
                    <button className="btn" style={{ position: 'relative', zIndex: 50, pointerEvents: 'auto', padding: '4px 10px', fontSize: '12px', background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'none' }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); setFile(null); }}>Remove</button>
                 </div>
                 {file.type.startsWith('image/') ? (
                    <img src={filePreview} alt="Preview" style={{ width: '100%', maxHeight: '400px', objectFit: 'contain', borderRadius: '8px', background: 'rgba(0,0,0,0.5)' }} />
                 ) : file.type === 'application/pdf' ? (
                    <iframe src={filePreview} style={{ width: '100%', height: '400px', border: 'none', borderRadius: '8px', background: 'white' }} title="PDF Preview" />
                 ) : (
                    <div style={{ padding: '30px', color: 'var(--text-muted)' }}>Preview not available for this file type</div>
                 )}
              </div>
            )}
          </div>

          {uploadSuccess && <div style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', padding: '12px', borderRadius: '8px', textAlign: 'center', fontWeight: 'bold', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}><CheckCircle size={18}/> Upload Successful!</div>}

          <button className="btn w-full" onClick={handleUpload} style={{ padding: '14px', fontSize: '15px', fontWeight: 600, display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <Upload size={20} /> Upload & Prepare for Evaluation
          </button>
        </div>
      </div>
      )}
      
      <div style={{ flex: showUpload ? 1 : 0.8, width: '100%', maxWidth: showUpload ? 'none' : '1000px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 className="title" style={{marginBottom: 0}}>Evaluation Queue</h2>
          {pending.length > 0 && 
            <button className="btn" onClick={handleEvaluateAll}>Evaluate All Pending</button>
          }
        </div>
        
        {evalSuccess && <div style={{ background: 'rgba(16, 185, 129, 0.2)', color: '#10b981', padding: '10px', borderRadius: '8px', textAlign: 'center', marginTop: '15px', fontWeight: 'bold', animation: 'fadeIn 0.3s ease-out' }}>🎉 {evalSuccess} Check the Results tab!</div>}

        <div className="glass-panel" style={{ padding: '20px', minHeight: '400px', marginTop: '30px' }}>
           {pending.map(p => (
              <div key={p.id} className="glass-card" style={{ marginBottom: '15px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {p.file_name} 
                        <span className="badge badge-pending" style={{background: 'rgba(59,130,246,0.2)', color: '#60a5fa'}}>{p.exam_type || 'Exam'}</span>
                        <span className="badge badge-success" style={{background: 'rgba(16,185,129,0.2)', color: '#10b981'}}>Div {p.division || 'A'}</span>
                        {p.course_name && <span className="badge" style={{background: 'rgba(139,92,246,0.2)', color: '#a78bfa'}}>{p.course_name}</span>}
                      </div>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>{p.exam_name} • {p.student_name} ({p.student_id})</div>
                    </div>
                    {evaluatingIds.has(p.id) ? (
                        <div className="badge badge-pending animate-pulse"><Clock size={12} style={{marginRight: '4px'}}/> Evaluating ({formatTime(timers[p.id] || 0)})...</div>
                    ) : (
                        <button className="btn" style={{ position: 'relative', zIndex: 50, pointerEvents: 'auto' }} onClick={(e) => { e.preventDefault(); e.stopPropagation(); handleEvaluate(p.id); }}>Evaluate Now</button>
                    )}
                 </div>
              </div>
           ))}
           {pending.length === 0 && <div style={{color:'var(--text-muted)', textAlign:'center', marginTop:'100px'}}>Queue is empty.</div>}
        </div>
      </div>
    </div>
  );
}

function ResultsView() {
  const [results, setResults] = useState([]);
  const [previewPdf, setPreviewPdf] = useState(null);

  const fetchResults = () => axios.get(`${API_BASE}/evaluations/results`).then(r => setResults(r.data));

  useEffect(() => {
    fetchResults();
  }, []);

  const handlePreview = (path, originalName) => {
    try {
      const url = `${API_BASE}/download?path=${encodeURIComponent(path)}`;
      setPreviewPdf({
        url,
        filename: `report_${originalName}.pdf`
      });
    } catch(e) {
      alert("Failed to load PDF preview");
    }
  };

  const handleClearHistory = async () => {
    if(confirm("Are you sure? This will permanently delete all evaluations, submissions, and reports.")) {
      try {
        await axios.delete(`${API_BASE}/evaluations/clear`);
        fetchResults();
        alert("History cleared successfully!");
      } catch (e) {
        alert("Failed to clear history");
      }
    }
  };

  return (
    <>
      <div className="animate-fade-in">
        <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', marginBottom: '20px' }}>
         <button className="btn btn-ghost" style={{ color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)' }} onClick={handleClearHistory}>
           <Trash2 size={16}/> Clear History
         </button>
      </div>

      <div className="glass-panel" style={{ padding: '20px' }}>
         <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--glass-border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '15px' }}>Student</th>
                <th style={{ padding: '15px' }}>Exam</th>
                <th style={{ padding: '15px' }}>Type/Div</th>
                <th style={{ padding: '15px' }}>Score</th>
                <th style={{ padding: '15px' }}>Grade</th>
                <th style={{ padding: '15px' }}>Model</th>
                <th style={{ padding: '15px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
               {results.map(r => (
                  <tr key={r.sub_id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                     <td style={{ padding: '15px', fontWeight: 500 }}>{r.student_name} <br/><span style={{fontSize:'12px', color:'var(--text-muted)'}}>{r.student_id}</span></td>
                     <td style={{ padding: '15px', color: 'var(--text-muted)' }}>{r.exam_name || 'N/A'}</td>
                     <td style={{ padding: '15px' }}>
                        <span className="badge badge-pending" style={{background: 'rgba(59,130,246,0.1)', color: '#60a5fa', marginRight: '5px', padding: '4px 8px'}}>{r.exam_type || 'ISA-1'}</span>
                        <span className="badge badge-success" style={{background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '4px 8px', marginRight: '5px'}}>Div {r.division || 'A'}</span>
                        {r.course_name && <span className="badge" style={{background: 'rgba(139,92,246,0.1)', color: '#a78bfa', padding: '4px 8px'}}>{r.course_name}</span>}
                     </td>
                     <td style={{ padding: '15px', fontWeight: 700, color: 'var(--accent)' }}>{r.total_marks} / {r.max_marks}</td>
                     <td style={{ padding: '15px' }}><div className="badge badge-success">{r.grade}</div></td>
                     <td style={{ padding: '15px' }}>
                        <span className="badge" style={{ background: r.model_used?.includes('Gemini') ? 'rgba(59,130,246,0.15)' : 'rgba(245,158,11,0.15)', color: r.model_used?.includes('Gemini') ? '#60a5fa' : '#fbbf24', padding: '4px 10px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <Brain size={12}/> {r.model_used || 'unknown'}
                        </span>
                     </td>
                     <td style={{ padding: '15px' }}>
                        <button className="btn" onClick={() => handlePreview(r.pdf_path, r.file_name)}>Preview Report</button>
                     </td>
                  </tr>
               ))}
               {results.length === 0 && <tr><td colSpan={7} style={{textAlign:'center', padding:'30px'}}>No results yet.</td></tr>}
            </tbody>
         </table>
      </div>
      </div>

      {previewPdf && (
        <div style={{
           position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
           background: 'rgba(0,0,0,0.85)', zIndex: 9999, backdropFilter: 'blur(5px)',
           display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem'
        }}>
           <div className="animate-fade-in" style={{ position: 'relative', background: 'rgba(15,23,42,0.95)', width: '100%', height: '90vh', maxWidth: '1200px', borderRadius: '16px', border: '1px solid var(--glass-border)', boxShadow: '0 25px 50px -12px rgba(0,0,0,1)', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '70px', padding: '0 25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                 <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                   <FileText color="var(--accent)" /> 
                   <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>{previewPdf.filename}</h3>
                 </div>
                 <div style={{ display: 'flex', gap: '15px' }}>
                    <button className="btn" style={{ background: 'var(--accent)', color: 'white', border: 'none', display: 'flex', gap: '8px', alignItems: 'center', padding: '8px 16px' }} onClick={() => {
                        const link = document.createElement('a');
                        link.href = previewPdf.url;
                        link.download = previewPdf.filename;
                        link.click();
                    }}><Upload size={16} style={{ transform: 'rotate(180deg)' }}/> Download PDF</button>
                    <button className="btn" style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: 'none', padding: '8px 16px' }} onClick={() => {
                        setPreviewPdf(null);
                    }}>Close</button>
                 </div>
              </div>
              <div style={{ position: 'absolute', top: '70px', left: 0, right: 0, bottom: 0 }}>
                 <iframe src={previewPdf.url} style={{ width: '100%', height: '100%', border: 'none', display: 'block', background: '#334155' }} title="Report Preview" />
              </div>
           </div>
        </div>
      )}

    </>
  );
}

function AnalyticsView() {
  const [detailed, setDetailed] = useState(null);
  const [grades, setGrades] = useState([]);
  const [filterDiv, setFilterDiv] = useState('All');
  const [filterExam, setFilterExam] = useState('All');
  const [filterCourse, setFilterCourse] = useState('All');

  useEffect(() => {
    const params = new URLSearchParams();
    if (filterDiv !== 'All') params.append('division', filterDiv);
    if (filterExam !== 'All') params.append('exam_type', filterExam);
    if (filterCourse !== 'All') params.append('course_name', filterCourse);
    
    axios.get(`${API_BASE}/analytics/detailed?${params.toString()}`).then(r => setDetailed(r.data));
    axios.get(`${API_BASE}/analytics/grades?${params.toString()}`).then(r => setGrades(r.data));
  }, [filterDiv, filterExam, filterCourse]);

  if (!detailed) return <div style={{padding: '40px', color: 'var(--text-muted)'}}>Loading analytics...</div>;

  return (
    <div className="animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '15px' }}>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '150px' }}>
            <select value={filterDiv} onChange={e=>setFilterDiv(e.target.value)} style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--glass-border)' }}>
              <option value="All" style={{color: 'black'}}>All Divisions</option>
              {['A', 'B', 'C', 'D', 'E'].map(d => <option key={d} value={d} style={{color: 'black'}}>Div {d}</option>)}
            </select>
          </div>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '150px' }}>
            <select value={filterExam} onChange={e=>setFilterExam(e.target.value)} style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--glass-border)' }}>
              <option value="All" style={{color: 'black'}}>All Exams</option>
              {['ISA-1', 'ISA-2', 'ESA'].map(t => <option key={t} value={t} style={{color: 'black'}}>{t}</option>)}
            </select>
          </div>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '150px' }}>
            <select value={filterCourse} onChange={e=>setFilterCourse(e.target.value)} style={{ padding: '10px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--glass-border)' }}>
              <option value="All" style={{color: 'black'}}>All Courses</option>
              {['GenAI', 'Cloud Computing'].map(c => <option key={c} value={c} style={{color: 'black'}}>{c}</option>)}
            </select>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        
        {/* Pass/Fail Ratio */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h4 style={{ marginBottom: '20px', color: 'white', fontWeight: 600 }}>Pass vs Fail Ratio</h4>
          <div style={{ height: '300px' }}>
            {detailed.pass_fail[0].value > 0 || detailed.pass_fail[1].value > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={detailed.pass_fail} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={5} dataKey="value">
                    <Cell fill="#10b981" />
                    <Cell fill="#ef4444" />
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px', color: 'white' }} />
                  <Legend verticalAlign="bottom" height={36}/>
                </PieChart>
              </ResponsiveContainer>
            ) : <div style={{ color: 'var(--text-muted)' }}>No data yet.</div>}
          </div>
        </div>

        {/* Grade Distribution */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h4 style={{ marginBottom: '20px', color: 'white', fontWeight: 600 }}>Grade Distribution</h4>
          <div style={{ height: '300px' }}>
            {grades.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={grades} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: 'white' }} />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div style={{ color: 'var(--text-muted)' }}>No grades data yet.</div>}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Division Wise Avg */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h4 style={{ marginBottom: '20px', color: 'white', fontWeight: 600 }}>Division Performance (%)</h4>
          <div style={{ height: '300px' }}>
            {detailed.division_data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={detailed.division_data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <YAxis dataKey="name" type="category" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} width={80} />
                  <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: 'white' }} />
                  <Bar dataKey="avg_score" fill="#3b82f6" radius={[0, 4, 4, 0]} barSize={30} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div style={{ color: 'var(--text-muted)' }}>No division data yet.</div>}
          </div>
        </div>

        {/* Exam Type Avg */}
        <div className="glass-panel" style={{ padding: '24px' }}>
          <h4 style={{ marginBottom: '20px', color: 'white', fontWeight: 600 }}>Exam Type Performance (%)</h4>
          <div style={{ height: '300px' }}>
            {detailed.exam_type_data.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={detailed.exam_type_data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: 'white' }} />
                  <Line type="monotone" dataKey="avg_score" stroke="#10b981" strokeWidth={3} dot={{ r: 6, fill: '#34d399', strokeWidth: 0 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div style={{ color: 'var(--text-muted)' }}>No exam type data yet.</div>}
          </div>
        </div>
      </div>

      {/* Question Level Breakdown */}
      <div className="glass-panel" style={{ padding: '24px', marginBottom: '40px' }}>
        <h4 style={{ marginBottom: '20px', color: 'white', fontWeight: 600 }}>Question-level Average Accuracy (%)</h4>
        <div style={{ height: '350px' }}>
          {detailed.question_data.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={detailed.question_data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="q_no" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip cursor={{ fill: 'rgba(255,255,255,0.05)' }} contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: 'white' }} />
                <Bar dataKey="avg_pct" fill="#f59e0b" radius={[4, 4, 0, 0]} barSize={40} />
              </BarChart>
            </ResponsiveContainer>
          ) : <div style={{ color: 'var(--text-muted)' }}>No question data yet.</div>}
        </div>
      </div>
    </div>
  );
}

function SettingsView() {
  const [settings, setSettings] = useState({
    gemini_api_key: '',
    ai_provider: 'ollama',
    ollama_model: 'llama3',
    institute_name: 'EvalAI Institute'
  });
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/settings`).then(r => setSettings(r.data));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await axios.post(`${API_BASE}/settings`, settings);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (e) {
      alert("Failed to save settings");
    } finally {
      setIsSaving(false);
    }
  };

  const handleFactoryReset = async () => {
    if(confirm("DANGER! This will permanently delete ALL data including teachers, students, courses, exams, and evaluations. The database will be completely reset. Are you absolutely sure?")) {
      const confirmation = prompt("Type 'RESET' to confirm.");
      if (confirmation === 'RESET') {
        try {
          await axios.post(`${API_BASE}/settings/reset_db`);
          alert("Database reset successfully! You will be logged out.");
          window.location.reload();
        } catch (e) {
          alert("Failed to reset database");
        }
      }
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: '900px', margin: '0 auto' }}>

      <div style={{ display: 'grid', gap: '30px', marginTop: '30px' }}>
        {/* AI Configuration */}
        <div className="glass-panel" style={{ padding: '30px' }}>
          <h3 style={{ borderBottom: '1px solid var(--glass-border)', paddingBottom: '15px', marginBottom: '20px', color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Brain size={20}/> Artificial Intelligence Configuration
          </h3>
          
          <div style={{ display: 'flex', gap: '20px', marginBottom: '20px' }}>
            <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
              <label>AI Evaluation Provider</label>
              <select value={settings.ai_provider} onChange={e=>setSettings({...settings, ai_provider: e.target.value})} style={{ padding: '12px', borderRadius: '8px', background: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--glass-border)' }}>
                <option value="ollama" style={{color: 'black'}}>Local Ollama (Llama 3)</option>
                <option value="gemini" style={{color: 'black'}}>Google Gemini API (Cloud)</option>
              </select>
            </div>
            
            {settings.ai_provider === 'ollama' ? (
              <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
                <label>Ollama Model Name</label>
                <input value={settings.ollama_model} onChange={e=>setSettings({...settings, ollama_model: e.target.value})} placeholder="e.g. llama3" />
              </div>
            ) : (
              <div className="input-container" style={{ flex: 1, marginBottom: 0 }}>
                <label>Google Gemini API Key</label>
                <input type="password" value={settings.gemini_api_key} onChange={e=>setSettings({...settings, gemini_api_key: e.target.value})} placeholder="AIzaSy..." />
              </div>
            )}
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Note: Local Ollama is completely free and private. Google Gemini may incur cloud API costs but offers higher accuracy for complex rubrics.</p>
        </div>

        {/* General Configuration */}
        <div className="glass-panel" style={{ padding: '30px' }}>
          <h3 style={{ borderBottom: '1px solid var(--glass-border)', paddingBottom: '15px', marginBottom: '20px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={20}/> General Details
          </h3>
          <div className="input-container" style={{ maxWidth: '400px' }}>
            <label>Institute Name</label>
            <input value={settings.institute_name} onChange={e=>setSettings({...settings, institute_name: e.target.value})} placeholder="e.g. Stanford University" />
          </div>
        </div>

        {/* Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button className="btn" onClick={handleSave} disabled={isSaving} style={{ padding: '12px 24px', fontSize: '15px', display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--accent)' }}>
            <CheckCircle size={18}/> {isSaving ? 'Saving...' : 'Save All Settings'}
          </button>
          {saveSuccess && <span style={{ color: '#10b981', fontWeight: 600, animation: 'fadeIn 0.3s ease-out' }}>Settings saved successfully!</span>}
        </div>

        {/* Danger Zone */}
        <div className="glass-panel" style={{ padding: '30px', border: '1px solid rgba(239, 68, 68, 0.3)', background: 'rgba(239, 68, 68, 0.05)', marginTop: '20px' }}>
          <h3 style={{ borderBottom: '1px solid rgba(239, 68, 68, 0.2)', paddingBottom: '15px', marginBottom: '20px', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Trash2 size={20}/> Danger Zone
          </h3>
          <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>Permanently erase all system data. This action cannot be undone.</p>
          <button className="btn" onClick={handleFactoryReset} style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#ef4444', border: '1px solid #ef4444' }}>
            Factory Reset Database
          </button>
        </div>

      </div>
    </div>
  );
}

// Utility: Download a chart container as PNG
function downloadChartAsPng(containerId, filename) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const svg = container.querySelector('svg');
  if (!svg) return;
  
  const svgData = new XMLSerializer().serializeToString(svg);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  const img = new Image();
  
  const svgRect = svg.getBoundingClientRect();
  canvas.width = svgRect.width * 2;
  canvas.height = svgRect.height * 2;
  ctx.scale(2, 2);
  
  img.onload = () => {
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    const link = document.createElement('a');
    link.download = `${filename}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  };
  img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
}

const MODEL_COLORS = { gemini: '#60a5fa', ollama: '#fbbf24' };
function getModelColor(name) {
  if (!name) return '#94a3b8';
  const n = name.toLowerCase();
  if (n.includes('gemini')) return MODEL_COLORS.gemini;
  return MODEL_COLORS.ollama;
}

function ModelComparisonView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    setLoading(true);
    axios.get(`${API_BASE}/analytics/model_comparison`).then(r => {
      setData(r.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-fade-in" style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>Loading comparison data...</div>;
  if (!data || data.model_stats.length === 0) return (
    <div className="animate-fade-in" style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>
      <GitCompare size={48} style={{ opacity: 0.2, marginBottom: '16px' }}/>
      <h3 style={{ color: 'white', marginBottom: '8px' }}>No Comparison Data Yet</h3>
      <p>Evaluate papers with both Gemini and Ollama to see comparison results here.</p>
    </div>
  );

  const models = data.model_stats.map(m => m.model_used);
  
  // --- Chart 1: Overall Avg Score per model ---
  const overallData = data.model_stats.map(m => ({ name: m.model_used, 'Avg Score %': m.avg_pct, Papers: m.count }));
  
  // --- Chart 2: Grade distribution grouped ---
  const allGrades = ['A+', 'A', 'B', 'C', 'F'];
  const gradeChartData = allGrades.map(g => {
    const row = { grade: g };
    models.forEach(m => {
      const match = data.grade_dist.find(d => d.model_used === m && d.grade === g);
      row[m] = match ? match.count : 0;
    });
    return row;
  });
  
  // --- Chart 3: Course-wise comparison ---
  const courseNames = [...new Set(data.course_model.map(c => c.course_name))];
  const courseChartData = courseNames.map(cn => {
    const row = { course: cn };
    models.forEach(m => {
      const match = data.course_model.find(d => d.course_name === cn && d.model_used === m);
      row[m] = match ? match.avg_pct : 0;
    });
    return row;
  });
  
  // --- Chart 4: Question-level ---
  const qNos = [...new Set(data.question_data.map(q => q.q_no))].sort();
  const qChartData = qNos.map(qn => {
    const row = { question: qn };
    models.forEach(m => {
      const match = data.question_data.find(d => d.q_no === qn && d.model === m);
      row[m] = match ? match.avg_marks : 0;
    });
    return row;
  });

  const tooltipStyle = { background: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: 'white', fontSize: '12px' };

  const ChartHeader = ({ title, chartId, filename }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
      <h4 style={{ color: 'white', fontWeight: 600, fontSize: '14px', margin: 0 }}>{title}</h4>
      <button onClick={() => downloadChartAsPng(chartId, filename)} className="btn" style={{ padding: '5px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '5px' }}>
        <Download size={12}/> PNG
      </button>
    </div>
  );

  return (
    <div className="animate-fade-in">
      
      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${models.length}, 1fr)`, gap: '14px', marginBottom: '24px' }}>
        {data.model_stats.map(m => (
          <div key={m.model_used} className="glass-card" style={{ borderTop: `3px solid ${getModelColor(m.model_used)}` }}>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, letterSpacing: '1px', marginBottom: '10px' }}>
              {m.model_used}
            </div>
            <div style={{ display: 'flex', gap: '20px', alignItems: 'baseline' }}>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 800, color: getModelColor(m.model_used), lineHeight: 1 }}>{m.avg_pct}%</div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Avg Score</div>
              </div>
              <div>
                <div style={{ fontSize: '24px', fontWeight: 800, color: 'white', lineHeight: 1 }}>{m.count}</div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>Papers</div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        
        {/* Overall Avg Score */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <ChartHeader title="Average Score by Model" chartId="chart-overall" filename="model_avg_score" />
          <div id="chart-overall" style={{ height: '280px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overallData} barSize={50}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="Avg Score %" radius={[6, 6, 0, 0]}>
                  {overallData.map((entry, i) => <Cell key={i} fill={getModelColor(entry.name)} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Grade Distribution */}
        <div className="glass-panel" style={{ padding: '22px' }}>
          <ChartHeader title="Grade Distribution by Model" chartId="chart-grades" filename="model_grade_distribution" />
          <div id="chart-grades" style={{ height: '280px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={gradeChartData} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="grade" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={tooltipStyle} />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
                {models.map(m => <Bar key={m} dataKey={m} fill={getModelColor(m)} radius={[4, 4, 0, 0]} barSize={30} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        
        {/* Course-wise */}
        {courseChartData.length > 0 && (
          <div className="glass-panel" style={{ padding: '22px' }}>
            <ChartHeader title="Course-wise Avg Score (%)" chartId="chart-course" filename="model_course_comparison" />
            <div id="chart-course" style={{ height: '280px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={courseChartData} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="course" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  {models.map(m => <Bar key={m} dataKey={m} fill={getModelColor(m)} radius={[4, 4, 0, 0]} barSize={40} />)}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
        
        {/* Question-level */}
        {qChartData.length > 0 && (
          <div className="glass-panel" style={{ padding: '22px' }}>
            <ChartHeader title="Question-wise Avg Marks" chartId="chart-question" filename="model_question_comparison" />
            <div id="chart-question" style={{ height: '280px' }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={qChartData} barGap={4}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="question" stroke="#94a3b8" fontSize={11} tickLine={false} />
                  <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  {models.map(m => <Bar key={m} dataKey={m} fill={getModelColor(m)} radius={[4, 4, 0, 0]} barSize={30} />)}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Student-level Comparison Table */}
      {data.student_scores.length > 0 && (
        <div className="glass-panel" style={{ padding: '22px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h4 style={{ color: 'white', fontWeight: 600, fontSize: '14px', margin: 0 }}>Per-Student Score Comparison</h4>
            <button onClick={() => {
              // CSV export
              const rows = [['Student', 'Course', 'Exam', 'Model', 'Score', 'Max', 'Percentage', 'Grade']];
              data.student_scores.forEach(s => {
                const pct = s.max_marks > 0 ? ((s.total_score / s.max_marks) * 100).toFixed(1) : '0';
                rows.push([s.student_name, s.course_name, s.exam_type, s.model_used, s.total_score, s.max_marks, pct, s.grade]);
              });
              const csv = rows.map(r => r.join(',')).join('\n');
              const blob = new Blob([csv], { type: 'text/csv' });
              const link = document.createElement('a');
              link.download = 'model_comparison_data.csv';
              link.href = URL.createObjectURL(blob);
              link.click();
            }} className="btn" style={{ padding: '5px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <Download size={12}/> Export CSV
            </button>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--glass-border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Student</th>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Course</th>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Exam</th>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Model</th>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Score</th>
                <th style={{ padding: '10px 12px', fontSize: '11px' }}>Grade</th>
              </tr>
            </thead>
            <tbody>
              {data.student_scores.map((s, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(255,255,255,0.03)' }}>
                  <td style={{ padding: '10px 12px', fontSize: '13px', fontWeight: 500 }}>{s.student_name}</td>
                  <td style={{ padding: '10px 12px', fontSize: '12px', color: 'var(--text-muted)' }}>{s.course_name}</td>
                  <td style={{ padding: '10px 12px', fontSize: '12px', color: 'var(--text-muted)' }}>{s.exam_type}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="badge" style={{ background: getModelColor(s.model_used) + '20', color: getModelColor(s.model_used), padding: '3px 8px', fontSize: '11px' }}>
                      {s.model_used}
                    </span>
                  </td>
                  <td style={{ padding: '10px 12px', fontSize: '13px', fontWeight: 600 }}>{s.total_score}/{s.max_marks}</td>
                  <td style={{ padding: '10px 12px' }}>
                    <span className="badge" style={{ background: s.grade === 'F' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)', color: s.grade === 'F' ? '#ef4444' : '#10b981', padding: '3px 8px', fontSize: '11px' }}>{s.grade}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AiInsightsView() {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filterDiv, setFilterDiv] = useState('All');
  const [filterExam, setFilterExam] = useState('All');
  const [filterCourse, setFilterCourse] = useState('All');

  const generateInsights = async () => {
    setLoading(true);
    setInsights(null);
    try {
      const params = new URLSearchParams();
      if (filterDiv !== 'All') params.append('division', filterDiv);
      if (filterExam !== 'All') params.append('exam_type', filterExam);
      if (filterCourse !== 'All') params.append('course_name', filterCourse);
      
      const res = await axios.get(`${API_BASE}/ai_insights/generate?${params.toString()}`);
      setInsights(res.data);
    } catch (e) {
      alert("Failed to generate AI insights.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: '1000px', margin: '0 auto', paddingBottom: '40px' }}>
      <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', marginBottom: '30px', padding: '15px 20px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(10px)' }}>

        <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '130px' }}>
            <select value={filterDiv} onChange={e=>setFilterDiv(e.target.value)} style={{ padding: '10px 15px', borderRadius: '10px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer' }}>
              <option value="All" style={{color: 'black'}}>All Divisions</option>
              {['A', 'B', 'C', 'D', 'E'].map(d => <option key={d} value={d} style={{color: 'black'}}>Div {d}</option>)}
            </select>
          </div>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '130px' }}>
            <select value={filterExam} onChange={e=>setFilterExam(e.target.value)} style={{ padding: '10px 15px', borderRadius: '10px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer' }}>
              <option value="All" style={{color: 'black'}}>All Exams</option>
              {['ISA-1', 'ISA-2', 'ESA'].map(t => <option key={t} value={t} style={{color: 'black'}}>{t}</option>)}
            </select>
          </div>
          <div className="input-container" style={{ marginBottom: 0, minWidth: '130px' }}>
            <select value={filterCourse} onChange={e=>setFilterCourse(e.target.value)} style={{ padding: '10px 15px', borderRadius: '10px', background: 'rgba(0,0,0,0.2)', color: 'white', border: '1px solid rgba(255,255,255,0.1)', cursor: 'pointer' }}>
              <option value="All" style={{color: 'black'}}>All Courses</option>
              {['GenAI', 'Cloud Computing'].map(c => <option key={c} value={c} style={{color: 'black'}}>{c}</option>)}
            </select>
          </div>
          <button 
            className="btn" 
            onClick={generateInsights} 
            disabled={loading} 
            style={{ 
              background: 'linear-gradient(135deg, #2563eb, #7c3aed)', 
              border: 'none', 
              padding: '12px 24px', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '10px',
              fontSize: '1rem',
              boxShadow: '0 4px 15px rgba(124, 58, 237, 0.3)',
              transition: 'all 0.3s ease'
            }}
          >
             {loading ? <span className="animate-pulse">Synthesizing...</span> : <><Brain size={18}/> Generate Report</>}
          </button>
        </div>
      </div>

      <div style={{ position: 'relative' }}>
        {/* Empty State */}
        {!insights && !loading && (
          <div className="glass-panel" style={{ padding: '60px 30px', textAlign: 'center', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
             <div style={{ width: '100px', height: '100px', borderRadius: '50%', background: 'rgba(255,255,255,0.02)', border: '1px dashed rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '25px' }}>
               <Brain size={48} style={{ opacity: 0.3, color: '#60a5fa' }} />
             </div>
             <h3 style={{ fontSize: '1.4rem', marginBottom: '10px', color: 'white' }}>Ready for Analysis</h3>
             <p style={{ fontSize: '1rem', color: 'var(--text-muted)', maxWidth: '400px', lineHeight: '1.6' }}>
               Select your target demographic and initialize the neural engine to extract hidden patterns from grading data.
             </p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="glass-panel" style={{ padding: '60px 30px', textAlign: 'center', minHeight: '400px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative', overflow: 'hidden' }}>
             <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: '3px', background: 'linear-gradient(90deg, transparent, #3b82f6, #8b5cf6, transparent)', animation: 'slide-right 2s linear infinite' }} />
             
             <div style={{ position: 'relative', width: '120px', height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '30px' }}>
               <div style={{ position: 'absolute', width: '100%', height: '100%', border: '2px solid rgba(59, 130, 246, 0.2)', borderRadius: '50%', animation: 'spin 3s linear infinite', borderTopColor: '#3b82f6' }} />
               <div style={{ position: 'absolute', width: '80%', height: '80%', border: '2px solid rgba(139, 92, 246, 0.2)', borderRadius: '50%', animation: 'spin-reverse 2s linear infinite', borderBottomColor: '#8b5cf6' }} />
               <Brain size={40} color="#60a5fa" className="animate-pulse" />
             </div>
             
             <h3 style={{ fontSize: '1.3rem', color: '#60a5fa', marginBottom: '10px', letterSpacing: '1px' }}>PROCESSING QUANTITATIVE METRICS</h3>
             <p style={{ color: 'var(--text-muted)', animation: 'pulse 1.5s ease-in-out infinite' }}>Correlating question marks with qualitative comments...</p>
          </div>
        )}

        {/* Results State */}
        {insights && !loading && (
          <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
             
             {/* Executive Summary */}
             <div className="glass-panel" style={{ padding: '30px', position: 'relative', overflow: 'hidden', borderLeft: '4px solid #3b82f6' }}>
               <div style={{ position: 'absolute', top: '-50px', right: '-50px', width: '150px', height: '150px', background: 'radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%)', borderRadius: '50%' }}/>
               <h3 style={{ margin: '0 0 15px 0', color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
                 <BarChart3 size={20}/> Executive Summary
               </h3>
               <p style={{ margin: 0, fontSize: '1.1rem', lineHeight: '1.8', color: 'rgba(255,255,255,0.9)' }}>
                 {insights.summary}
               </p>
             </div>

             <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px' }}>
                {/* Strengths */}
                <div className="glass-panel" style={{ padding: '30px', background: 'linear-gradient(to bottom right, rgba(16, 185, 129, 0.05), transparent)', borderTop: '1px solid rgba(16, 185, 129, 0.2)' }}>
                  <h4 style={{ margin: '0 0 20px 0', color: '#10b981', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem' }}>
                    <div style={{ background: 'rgba(16, 185, 129, 0.1)', padding: '6px', borderRadius: '8px' }}>
                      <CheckCircle size={18}/>
                    </div>
                    Class Strengths
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {insights.strengths?.map((s, i) => (
                      <div key={i} className="animate-slide-up" style={{ animationDelay: `${i * 0.1}s`, display: 'flex', alignItems: 'flex-start', gap: '12px', background: 'rgba(0,0,0,0.2)', padding: '12px 16px', borderRadius: '8px', borderLeft: '2px solid #10b981' }}>
                        <span style={{ color: '#10b981', fontWeight: 'bold', fontSize: '0.9rem', marginTop: '2px' }}>0{i+1}</span>
                        <span style={{ lineHeight: '1.5', color: 'rgba(255,255,255,0.85)' }}>{s}</span>
                      </div>
                    ))}
                    {(!insights.strengths || insights.strengths.length === 0) && <div style={{color:'var(--text-muted)', padding: '10px'}}>No specific strengths identified.</div>}
                  </div>
                </div>

                {/* Weaknesses */}
                <div className="glass-panel" style={{ padding: '30px', background: 'linear-gradient(to bottom right, rgba(239, 68, 68, 0.05), transparent)', borderTop: '1px solid rgba(239, 68, 68, 0.2)' }}>
                  <h4 style={{ margin: '0 0 20px 0', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem' }}>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '6px', borderRadius: '8px' }}>
                      <FileText size={18}/>
                    </div>
                    Core Weaknesses
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {insights.weaknesses?.map((w, i) => (
                      <div key={i} className="animate-slide-up" style={{ animationDelay: `${i * 0.1}s`, display: 'flex', alignItems: 'flex-start', gap: '12px', background: 'rgba(0,0,0,0.2)', padding: '12px 16px', borderRadius: '8px', borderLeft: '2px solid #ef4444' }}>
                        <span style={{ color: '#ef4444', fontWeight: 'bold', fontSize: '0.9rem', marginTop: '2px' }}>0{i+1}</span>
                        <span style={{ lineHeight: '1.5', color: 'rgba(255,255,255,0.85)' }}>{w}</span>
                      </div>
                    ))}
                    {(!insights.weaknesses || insights.weaknesses.length === 0) && <div style={{color:'var(--text-muted)', padding: '10px'}}>No specific weaknesses identified.</div>}
                  </div>
                </div>
             </div>

             {/* Recommendations */}
             <div className="glass-panel" style={{ padding: '30px', background: 'linear-gradient(to right, rgba(245, 158, 11, 0.05), transparent)', borderLeft: '4px solid #f59e0b' }}>
                <h4 style={{ margin: '0 0 20px 0', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.1rem' }}>
                  <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '6px', borderRadius: '8px' }}>
                    <BookOpen size={18}/>
                  </div>
                  Strategic Recommendations
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '15px' }}>
                  {insights.recommendations?.map((r, i) => (
                    <div key={i} className="animate-slide-up" style={{ animationDelay: `${i * 0.1}s`, display: 'flex', alignItems: 'center', gap: '15px', background: 'rgba(255,255,255,0.02)', padding: '15px 20px', borderRadius: '10px', border: '1px solid rgba(245, 158, 11, 0.15)' }}>
                      <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', boxShadow: '0 0 10px #f59e0b' }} />
                      <span style={{ lineHeight: '1.5', color: 'rgba(255,255,255,0.9)' }}>{r}</span>
                    </div>
                  ))}
                  {(!insights.recommendations || insights.recommendations.length === 0) && <div style={{color:'var(--text-muted)', padding: '10px'}}>No specific recommendations.</div>}
                </div>
             </div>
             
          </div>
        )}
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        @keyframes spin-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        @keyframes slide-right {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        .animate-slide-up {
          opacity: 0;
          animation: slideUpFade 0.5s ease forwards;
        }
        @keyframes slideUpFade {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}} />
    </div>
  );
}

export default App;
