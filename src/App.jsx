import { Home } from './sections/Home.jsx'
import { Generate } from './sections/Generate.jsx';
import { Routes, Route, Router } from "@solidjs/router"
import './index.css'; 

function App() {
  return (
    <>
      <Router>
        <Routes>
          <Route path="/" component={Home} />
          <Route path="/generate" component={Generate} />
        </Routes>
      </Router>
    </>
  );
}

export default App;
