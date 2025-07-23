import React, { useState, useRef } from "react";
import styles from "./Login.module.css";
import flowerImg from "../flower3.png";
import flower2Img from "../flower5.png";

export default function Login({ onLogin }) {
  const [showSignup, setShowSignup] = useState(false);
  const pinkboxRef = useRef(null);

  // 注册表单受控数据
  const [registerData, setRegisterData] = useState({
    username: '',
    password: '',
    confirmPassword: ''
  });
  const [registerError, setRegisterError] = useState('');
  const [registerLoading, setRegisterLoading] = useState(false);

  // 登录表单受控数据
  const [loginData, setLoginData] = useState({
    username: '',
    password: ''
  });
  const [loginError, setLoginError] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);

  // 切换到注册
  const handleSignupClick = () => {
    if (pinkboxRef.current) {
      pinkboxRef.current.style.transform = "translateX(80%)";
    }
    setShowSignup(true);
  };
  // 切换到登录
  const handleSigninClick = () => {
    if (pinkboxRef.current) {
      pinkboxRef.current.style.transform = "translateX(0%)";
    }
    setShowSignup(false);
    setRegisterError('');
  };

  // 登录表单输入变化
  const handleLoginChange = (e) => {
    const { name, value } = e.target;
    setLoginData(prev => ({ ...prev, [name]: value }));
  };

  // 登录表单提交
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: loginData.username,
          password: loginData.password
        })
      });
      const data = await res.json();
      if (data.success) {
        setLoginLoading(false);
        onLogin(loginData.username); // 传递 user_id
      } else {
        setLoginError(data.message || 'Login failed.');
      }
    } catch (err) {
      setLoginError('Network error.');
    } finally {
      setLoginLoading(false);
    }
  };

  // 注册表单输入变化
  const handleRegisterChange = (e) => {
    const { name, value } = e.target;
    setRegisterData(prev => ({ ...prev, [name]: value }));
  };

  // 注册表单提交
  const handleRegister = async (e) => {
    e.preventDefault();
    setRegisterError('');
    if (!registerData.username || !registerData.password || !registerData.confirmPassword) {
      setRegisterError('Please fill in all fields.');
      return;
    }
    if (registerData.password !== registerData.confirmPassword) {
      setRegisterError('Passwords do not match.');
      return;
    }
    setRegisterLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: registerData.username,
          password: registerData.password
        })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setRegisterError(data.message || 'Registration failed.');
      } else {
        setRegisterLoading(false);
        handleSigninClick(); // 注册成功后切回登录
      }
    } catch (err) {
      setRegisterError('Network error.');
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <div className={styles["login-root"]}>
      <div className={styles.container}>
        <div className={styles.welcome}>
          <div className={styles.pinkbox} ref={pinkboxRef} style={{ transform: showSignup ? "translateX(80%)" : "translateX(0%)" }}>
            {/* 注册表单 */}
            <div className={showSignup ? styles.signup : styles.signup + ' ' + styles.nodisplay}>
              <h1>Register</h1>
              <form autoComplete="off" onSubmit={handleRegister}>
                <input type="text" name="username" placeholder="Username" className={styles["login-input"]} value={registerData.username} onChange={handleRegisterChange} />
                <input type="password" name="password" placeholder="Password" className={styles["login-input"]} value={registerData.password} onChange={handleRegisterChange} />
                <input type="password" name="confirmPassword" placeholder="Confirm Password" className={styles["login-input"]} value={registerData.confirmPassword} onChange={handleRegisterChange} />
                {registerError && <div style={{ color: 'red', fontSize: 12, marginBottom: 8 }}>{registerError}</div>}
                <button className={`${styles.button} ${styles.submit}`} type="submit" disabled={registerLoading}>{registerLoading ? 'Registering...' : 'Create Account'}</button>
              </form>
            </div>
            {/* 登录表单 */}
            <div className={!showSignup ? styles.signin : styles.signin + ' ' + styles.nodisplay}>
              <h1>Sign In</h1>
              <form className={styles["more-padding"]} autoComplete="off" onSubmit={handleLogin}>
                <input type="text" name="username" placeholder="Username" className={styles["login-input"]} value={loginData.username} onChange={handleLoginChange} />
                <input type="password" name="password" placeholder="Password" className={styles["login-input"]} value={loginData.password} onChange={handleLoginChange} />
                <div className={styles.checkbox}>
                  <input type="checkbox" id="remember" className={styles["login-checkbox"]} />
                  <label htmlFor="remember">Remember Me</label>
                </div>
                {loginError && <div style={{ color: 'red', fontSize: 12, marginBottom: 8 }}>{loginError}</div>}
                <button className={styles.submit} type="submit" disabled={loginLoading}>{loginLoading ? 'Logging in...' : 'Login'}</button>
              </form>
            </div>
          </div>
          {/* 左侧box */}
          <div className={styles.leftbox}>
            <h2 className={styles.title}><span>FILM</span>&<br />PILOT</h2>
            <p className={styles.desc}>Find your favorite <span>film</span></p>
            <img className={`${styles.flower} ${styles.smaller}`} src={flowerImg} alt="flower" />
            <p className={styles.account}>Have an account?</p>
            <button className={styles.button} onClick={handleSigninClick}>Login</button>
          </div>
          {/* 右侧box */}
          <div className={styles.rightbox}>
            <h2 className={styles.title}><span>FILM</span>&<br />PILOT</h2>
            <p className={styles.desc}>Find your favorite <span>film</span></p>
            <img className={styles.flower} src={flower2Img} alt="flower" />
            <p className={styles.account}>Don't have an account?</p>
            <button className={`${styles.button} ${styles.signupBtn}`} onClick={handleSignupClick}>Sign Up</button>
          </div>
        </div>
      </div>
    </div>
  );
} 