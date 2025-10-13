import React from 'react';
import PdfOcr from './components/PdfOcr';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>YouTube Utils - Media Tools</h1>
        <p>Professional media processing utilities</p>
      </header>

      <main>
        <PdfOcr />
      </main>

      <footer className="App-footer">
        <p>&copy; 2025 YouTube Utils. Built with React and FastAPI.</p>
      </footer>
    </div>
  );
}

export default App;