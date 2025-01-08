import { useState } from "react";
import Login from "./components/Login";
import Register from "./components/Register";
import Chat from "./components/Chat";

function App() {
  const [token, setToken] = useState(null);
  const [isRegistering, setIsRegistering] = useState(false);

  return (
    <div>
      {!token ? (
        isRegistering ? (
          <Register onRegister={() => setIsRegistering(false)} />
        ) : (
          <Login onLogin={setToken} />
        )
      ) : (
        <Chat token={token} />
      )}
      {!token && (
        <button onClick={() => setIsRegistering(!isRegistering)}>
          {isRegistering ? "Back to Login" : "Register"}
        </button>
      )}
    </div>
  );
}

export default App;
