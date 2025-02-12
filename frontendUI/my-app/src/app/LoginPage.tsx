import React from "react";
import Image from "next/image";
import "./LoginPage.css";

const LoginPage: React.FC = () => {
  return (
    <div className="login-page">
      <div className="login-container">
        <form>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input type="text" id="username" name="username" />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input type="password" id="password" name="password" />
          </div>
          <button type="submit">Login</button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
