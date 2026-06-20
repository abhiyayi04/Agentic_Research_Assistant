import ChatInterface from './components/ChatInterface'
import FileUpload from './components/FileUpload'

function App() {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem', fontFamily: 'sans-serif' }}>
      <h1 style={{ marginBottom: '0.25rem' }}>ContextPilot</h1>
      <p style={{ color: '#666', marginTop: 0, marginBottom: '2rem' }}>Multi-Agent Research Assistant</p>
      <FileUpload />
      <ChatInterface />
    </div>
  )
}

export default App
