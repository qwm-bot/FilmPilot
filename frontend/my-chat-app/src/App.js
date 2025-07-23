import React, { useState, useEffect, useRef } from "react";
import "./App.css";
import AmapRouteBox from "./components/AmapRouteBox"; // 导入地图组件
import Login from "./components/Login";

function App() {
  const [showSidebar, setShowSidebar] = useState(true);
  const [showOptions, setShowOptions] = useState(false);
  const [showAgeSettings, setShowAgeSettings] = useState(false);
  const [showTestSettings, setShowTestSettings] = useState(false);
  const [conversations, setConversations] = useState({});
  const [editingConversation, setEditingConversation] = useState(null);
  const [newName, setNewName] = useState("");
  const [currentConversation, setCurrentConversation] = useState(null);
  const [currentMessages, setCurrentMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [streamingBotMsg, setStreamingBotMsg] = useState("");
  const [theme, setTheme] = useState("day");
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  const [appState, setAppState] = useState("initial");
  const [isRecommendationExpanded, setIsRecommendationExpanded] = useState(false);
  const [isThinking, setIsThinking] = useState(false); // 思考状态
  const [routeData, setRouteData] = useState(null); // 存储路线数据
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userId, setUserId] = useState(() => localStorage.getItem('user_id') || '');

  // 状态：年龄范围、性别和电影偏好
  const [selectedAgeRange, setSelectedAgeRange] = useState("");
  const [selectedGender, setSelectedGender] = useState("");
  const [selectedMoviePreferences, setSelectedMoviePreferences] = useState([]);

  // 1. 新增 recommendations 状态
  const [recommendations, setRecommendations] = useState([]);

  // 新增：用户地理位置和权限询问状态
  const [userLocation, setUserLocation] = useState(null);
  const [locationPermissionAsked, setLocationPermissionAsked] = useState(false);
  // 新增：对话ID映射和自增ID
  const [conversationIdMap, setConversationIdMap] = useState({}); // name -> id
  const [nextConversationId, setNextConversationId] = useState(1); // 自增id

  const messagesEndRef = useRef(null);
  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const initialScreenRef = useRef(null);
  const ageRanges = ["18岁以下", "18-25", "26-35", "36-45", "45岁以上"];
  const genders = ["女", "男"];
  const movieGenres = ["剧情", "喜剧", "动作", "科幻", "爱情", "悬疑", "恐怖", "动画", "纪录片", "音乐剧"];
  
  // 增强的Markdown格式化函数（修复换行和引号问题）
  const formatBotMessage = (text, isStreaming = false) => {
    if (!text) return null;
    // 处理加粗文本：**bold**
    const boldRegex = /\*\*(.*?)\*\*/g;
    // 处理斜体文本：*italic*
    const italicRegex = /\*(.*?)\*/g;
    // 处理 Markdown 链接：[文字](链接)
    // 动态 className
    const linkRegex = isStreaming
      ? /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g
      : /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;
    const linkClass = isStreaming ? 'ticket-link disabled' : 'ticket-link';
    // 处理数字列表：1. item1\n2. item2
    const listRegex = /(\d+\.\s+.*?)(?=\n\d+\.|\n\n|$)/gs;
    // 按段落分割（连续两个换行视为段落分隔）
    const paragraphs = text.split('\n\n');
    return paragraphs.map((paragraph, pIndex) => {
      // 检查是否是列表
      if (paragraph.match(listRegex)) {
        const listItems = paragraph.split('\n').filter(item => item.trim());
        return (
          <div key={`p-${pIndex}`} className="message-list">
            {listItems.map((item, idx) => {
              // 处理链接、加粗、斜体和换行
              let processedItem = item
                .replace(linkRegex, `<a class=\"${linkClass}\" href=\"$2\" target=\"_blank\" rel=\"noopener noreferrer\">$1</a>`)
                .replace(boldRegex, '<strong>$1</strong>')
                .replace(italicRegex, '<em>$1</em>')
                .replace(/\n/g, '<br/>'); // 处理列表项内的换行
              return (
                <div key={`li-${idx}`} className="list-item" dangerouslySetInnerHTML={{ __html: processedItem }} />
              );
            })}
          </div>
        );
      }
      // 处理普通段落中的链接和换行符
      const htmlContent = paragraph
        .replace(linkRegex, `<a class=\"${linkClass}\" href=\"$2\" target=\"_blank\" rel=\"noopener noreferrer\">$1</a>`)
        .replace(/\n/g, '<br/>') // 关键修复：将所有\n转换为<br>
        .replace(boldRegex, '<strong>$1</strong>')
        .replace(italicRegex, '<em>$1</em>');
      return (
        <p 
          key={`p-${pIndex}`} 
          dangerouslySetInnerHTML={{ __html: htmlContent }} 
        />
      );
    });
  };

  // 初始化状态：响应式处理 + 本地存储恢复
  useEffect(() => {
    // 读取主题设置
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.className = savedTheme;
    }
    
    // 读取聊天数据
    const savedData = localStorage.getItem('chatData');
    if (savedData) {
      try {
        const { conversations: savedConvs, currentConv, messages, settings } = JSON.parse(savedData);
        setConversations(savedConvs || {});
        setCurrentConversation(currentConv);
        setCurrentMessages(messages || []);
        setSelectedAgeRange(settings?.ageRange || '');
        setSelectedGender(settings?.gender || '');
        setSelectedMoviePreferences(settings?.moviePrefs || []);
        
        // 如果有消息，进入聊天状态
        if (messages && messages.length > 0) {
          setAppState("chat");
        }
      } catch (e) {
        console.error('Failed to parse saved data', e);
      }
    }
    // 恢复输入框内容
    const savedInput = localStorage.getItem('chatInputValue');
    if (savedInput !== null) {
      setInputValue(savedInput);
    }
    // 响应式处理
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
      if (window.innerWidth >= 768) {
        setShowSidebar(true);
      } else {
        setShowSidebar(false);
      }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 保存数据到localStorage
  useEffect(() => {
    const dataToSave = {
      conversations,
      currentConv: currentConversation,
      messages: currentMessages,
      settings: {
        ageRange: selectedAgeRange,
        gender: selectedGender,
        moviePrefs: selectedMoviePreferences
      }
    };
    
    localStorage.setItem('chatData', JSON.stringify(dataToSave));
  }, [conversations, currentConversation, currentMessages, 
      selectedAgeRange, selectedGender, selectedMoviePreferences]);

  // 实时保存 inputValue 到 localStorage
  useEffect(() => {
    localStorage.setItem('chatInputValue', inputValue);
  }, [inputValue]);

  // 保存主题设置
  useEffect(() => {
    localStorage.setItem('theme', theme);
  }, [theme]);

  // 只在新消息完全输出后滚动到底部
  useEffect(() => {
    if (!streamingBotMsg) {
      scrollToBottom();
    }
    const hasMessages = currentMessages.length > 0;
    setAppState(hasMessages ? "chat" : "initial");
    if (inputRef.current && hasMessages) {
      inputRef.current.focus();
    }
  }, [currentMessages, streamingBotMsg]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const simulateStreamResponse = (text, conversationName) => {
    let i = 0;
    setStreamingBotMsg("");
    
    // 立即显示第一个字符，解决首字符显示问题
    if (text.length > 0) {
      setStreamingBotMsg(text[0]);
      i = 1;
    }
    
    const interval = setInterval(() => {
      if (i < text.length) {
        setStreamingBotMsg(prev => prev + text[i]);
        i++;
      } else {
        clearInterval(interval);
        const botMessage = { role: "bot", content: text };
        setCurrentMessages(msgs => [...msgs, botMessage]);
        setConversations(prev => ({
          ...prev,
          [conversationName]: {
            ...prev[conversationName],
            messages: [...prev[conversationName].messages, botMessage],
            time: new Date().toLocaleString('zh-CN', { 
              year: 'numeric', 
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            }).replace(',', '')
          }
        }));
        setStreamingBotMsg("");
      }
    }, 40);
  };

  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setUserLocation({ lat: latitude, lnt: longitude });
        },
        (error) => {
          setUserLocation({ lat: 38.988726, lnt: 117.346194 }); // 默认经纬度
        }
      );
    } else {
      setUserLocation({ lat: 38.988726, lnt: 117.346194 }); // 默认经纬度
    }
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;

    // 第一次发送消息时询问用户是否允许获取地理位置
    if (!locationPermissionAsked) {
      const allowLocation = window.confirm('是否允许获取您的地理位置？');
      setLocationPermissionAsked(true);
      if (allowLocation) {
        getUserLocation();
      } else {
        setUserLocation({ lat: 38.988726, lnt: 117.346194 }); // 默认经纬度
      }
    }

    const createNewConv = () => {
      const newId = nextConversationId;
      setNextConversationId(id => id + 1);
      const newName = `对话 ${Object.keys(conversations).length + 1}`;
      const currentTime = new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      }).replace(',', '');
      setConversationIdMap(prev => ({ ...prev, [newName]: newId }));
      const newConversation = {
        createdAt: currentTime,
        time: currentTime,
        messages: [],
        conversation_id: newId
      };
      setConversations(prev => ({ ...prev, [newName]: newConversation }));
      setCurrentConversation(newName);
      return { name: newName, id: newId };
    };

    let conversationName = currentConversation;
    let conversationId = null;
    if (!conversationName) {
      const { name, id } = createNewConv();
      conversationName = name;
      conversationId = id;
    } else {
      conversationId = conversationIdMap[conversationName] || (conversations[conversationName] && conversations[conversationName].conversation_id);
    }

    const newMessage = { role: "user", content: inputValue };
    const updatedMessages = [...currentMessages, newMessage];
    setCurrentMessages(updatedMessages);
    setConversations(prev => ({
      ...prev,
      [conversationName]: {
        ...prev[conversationName],
        messages: [...prev[conversationName].messages, newMessage],
        time: new Date().toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        }).replace(',', '')
      }
    }));
    setInputValue("");
    setAppState("chat");
    setIsThinking(true); // 开始思考

    try {
      const response = await fetch('http://localhost:8000/api/workflow', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currentInput: inputValue,
          ageRange: selectedAgeRange,
          gender: selectedGender,
          moviePreferences: selectedMoviePreferences,
          lat: userLocation ? userLocation.lat : 38.988726, // 默认纬度
          lnt: userLocation ? userLocation.lnt : 117.346194, // 默认经度
          conversation_id: conversationId // 传递自增数字id
        }),
      });
      if (!response.ok) throw new Error('API request failed');
      let data = await response.text();
      function tryParseJSON(d) {
        try {
          const parsed = JSON.parse(d);
          if (typeof parsed === 'string') return tryParseJSON(parsed);
          return parsed;
        } catch (e) { return null; }
      }
      const parsedData = tryParseJSON(data);
      if (parsedData && parsedData.map_action) {
        const routeData = {
          origin: parsedData.origin || null,
          destination: parsedData.destination,
          city: parsedData.city,
          mode: parsedData.mode,
          amapjs_key: "a64c3600e44f633e2af4fd8b0c8bb5eb",
          security_key: "57a82ef7ebde5553411673bc0ae7c6b2"
        };
        setIsThinking(false);
        setRouteData(routeData);
        return;
      }
      data = data.replace(/^"/, '').replace(/"$/, '');
      data = data.replace(/\\n/g, '\n'); 
      setIsThinking(false);
      simulateStreamResponse(data, conversationName);
    } catch (error) {
      console.error('Error:', error);
      setIsThinking(false);
      const errorMessage = { role: "bot", content: "抱歉，发生了一些错误，请稍后再试。" };
      setCurrentMessages(msgs => [...msgs, errorMessage]);
      setConversations(prev => ({
        ...prev,
        [conversationName]: {
          ...prev[conversationName],
          messages: [...prev[conversationName].messages, errorMessage],
          time: new Date().toLocaleString('zh-CN', { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          }).replace(',', '')
        }
      }));
    }
  };

  // 当获取到路线数据时，添加到消息中
  useEffect(() => {
    if (routeData) {
      const botMessage = { 
        role: "bot", 
        content: "已为您规划路线", 
        mapData: routeData 
      };
      
      setCurrentMessages(msgs => [...msgs, botMessage]);
      setConversations(prev => {
        const updated = { ...prev };
        if (currentConversation && updated[currentConversation]) {
          updated[currentConversation] = {
            ...updated[currentConversation],
            messages: [...updated[currentConversation].messages, botMessage],
            time: new Date().toLocaleString('zh-CN', { 
              year: 'numeric', 
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit'
            }).replace(',', '')
          };
        }
        return updated;
      });
      
      setRouteData(null);
    }
  }, [routeData, currentConversation]);

  const createNewConversation = () => {
    setCurrentConversation(null);
    setCurrentMessages([]);
    setInputValue("");
    setAppState("initial");
    setIsRecommendationExpanded(false);
    
    if (isMobile) {
      setShowSidebar(false);
    }
    
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }, 100);
  };

  const deleteConversation = (name, e) => {
    e.stopPropagation();
    const updatedConversations = { ...conversations };
    delete updatedConversations[name];
    setConversations(updatedConversations);
    if (currentConversation === name) {
      const remainingKeys = Object.keys(updatedConversations);
      if (remainingKeys.length > 0) {
        const firstKey = remainingKeys[0];
        setCurrentConversation(firstKey);
        setCurrentMessages(updatedConversations[firstKey].messages);
      } else {
        setCurrentConversation(null);
        setCurrentMessages([]);
        setAppState("initial");
      }
    }
  };

  const renameConversation = (name, e) => {
    e.stopPropagation();
    setEditingConversation(name);
    setNewName(name);
  };

  const handleRename = (e) => {
    e.stopPropagation();
    if (editingConversation && newName.trim()) {
      const updatedConversations = { ...conversations };
      if (updatedConversations[editingConversation]) {
        const conversationData = updatedConversations[editingConversation];
        delete updatedConversations[editingConversation];
        updatedConversations[newName] = conversationData;
        setConversations(updatedConversations);
        if (currentConversation === editingConversation) {
          setCurrentConversation(newName);
        }
      }
    }
    setEditingConversation(null);
  };

  const cancelRename = (e) => {
    e.stopPropagation();
    setEditingConversation(null);
  };

  const loadConversation = (name) => {
    const conversation = conversations[name];
    if (conversation) {
      setCurrentConversation(name);
      setCurrentMessages(conversation.messages);
      setAppState("chat");
    }
    if (isMobile) {
      setShowSidebar(false);
    }
  };

  const changeTheme = (newTheme) => {
    setTheme(newTheme);
    document.documentElement.className = newTheme;
  };

  const focusInput = () => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  // 页面加载时获取今日精选
  useEffect(() => {
    if (isLoggedIn) {
      fetch('http://localhost:8000/api/daily_recommendations?count=4')
        .then(res => res.json())
        .then(data => setRecommendations(Array.isArray(data) ? data : []))
        .catch(err => {
          setRecommendations([]);
          console.error('获取今日精选失败:', err);
        });
    }
  }, [isLoggedIn]);

  // 修改推荐栏切换函数：控制滚动和展开状态
  const toggleRecommendations = () => {
    setIsRecommendationExpanded(!isRecommendationExpanded);
    
    // 展开时禁止背景滚动
    if (!isRecommendationExpanded) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
  };

  const closeRecommendations = (e) => {
    e?.stopPropagation();
    setIsRecommendationExpanded(false);
    document.body.style.overflow = ''; // 恢复滚动
  };

  // MovieCard 组件适配新字段
  const MovieCard = ({ item }) => (
    <div className="movie-card">
      <div className="movie-poster" style={{ height: '300px' }}>
        {item.poster_url && typeof item.poster_url === 'string' && item.poster_url.trim() && item.poster_url !== '无' ? (
          <img src={item.poster_url} alt={item.title} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '12px 12px 0 0' }} onError={e => { e.target.onerror = null; e.target.style.display = 'none'; }} />
        ) : (
          <div className="movie-poster-placeholder">无海报</div>
        )}
      </div>
      <div className="movie-info">
        <h3 className="movie-title">{item.title}</h3>
        <div className="movie-meta">
          {item.year && <span className="movie-year">{item.year}</span>}
          {item.rating !== undefined && (
            <div className="movie-rating">
              <span className="stars">{item.rating ? '⭐'.repeat(Math.round(item.rating / 2)) : '☆☆☆☆☆'}</span>
              <span>{item.rating}</span>
            </div>
          )}
        </div>
        {item.tagline && (
          <div className="movie-tagline">
            {item.tagline.replace(/^['"“”「」]+|['"“”「」]+$/g, '')}
          </div>
        )}
        <div className="movie-footer">
          {item.director && <span>导演：{item.director}</span>}
          {item.country && <span>{item.country}</span>}
        </div>
      </div>
    </div>
  );

  // 修改RecommendationBar组件：添加遮罩层
  const RecommendationBar = ({ isExpanded }) => (
    <>
      <div 
        className={`recommendation-bar ${isExpanded ? 'expanded' : ''}`}
        onClick={isExpanded ? undefined : toggleRecommendations}
      >
        <div className="bar-header">
          <h2 className="section-title">今日精选</h2>
          {isExpanded && (
            <button 
              className="close-recommendations" 
              onClick={closeRecommendations}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          )}
        </div>
        {isExpanded ? (
          <div className="horizontal-movies-grid no-scroll">
            {Array.isArray(recommendations) && recommendations.length > 0 ? (
              recommendations.slice(0, 4).map(item => (
                <MovieCard key={item.id} item={item} />
              ))
            ) : (
              <div style={{ padding: 32, color: '#888' }}>暂无今日精选推荐</div>
            )}
          </div>
        ) : (
          <div className="recommendation-label">
            <span>点击展开今日精选推荐</span>
          </div>
        )}
      </div>
      
      {isExpanded && (
        <div 
          className="recommendation-overlay visible" 
          onClick={closeRecommendations}
        />
      )}
    </>
  );

  const sortedConversations = Object.entries(conversations).sort((a, b) => {
    return new Date(b[1].createdAt) - new Date(a[1].createdAt);
  });

  // 保存设置的函数
  const saveSettings = (type) => {
    if (type === 'age') {
      setShowAgeSettings(false);
    } else if (type === 'test') {
      setShowTestSettings(false);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setUserId("");
    localStorage.removeItem('user_id');
    // 可选：清空聊天记录、推荐等
    // setCurrentMessages([]);
    // setConversations({});
  };

  if (!isLoggedIn) {
    return <Login onLogin={() => setIsLoggedIn(true)} />;
  }

  return (
    <div className={`chat-app ${theme}`}>
      {isMobile && !showSidebar && appState !== "expanded" && appState !== "chat" && (
        <button className="mobile-menu-btn" onClick={() => setShowSidebar(true)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      )}
      
      <aside 
        className={`sidebar ${showSidebar ? 'open' : ''} ${isMobile ? 'mobile' : ''}`}
        style={!showSidebar && !isMobile ? { width: 0, padding: 0, overflow: 'hidden' } : { position: 'relative' }}
      >
        <div className="sidebar-header">
          <h2>聊天记录</h2>
          <div className="sidebar-controls">
            <button className="new-chat-btn" onClick={createNewConversation}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19"></line>
                <line x1="5" y1="12" x2="19" y2="12"></line>
              </svg>
              新对话
            </button>
            <button className="collapse-sidebar" onClick={() => setShowSidebar(false)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </button>
          </div>
        </div>
        <div className="conversations-list" style={{ overflowY: 'auto', flex: 1, marginBottom: '80px' }}>
          {Object.keys(conversations).length > 0 ? (
            sortedConversations.map(([name, convo], idx) => (
              <div 
                key={idx} 
                className={`conversation-item ${currentConversation === name ? 'active' : ''}`}
                onClick={() => loadConversation(name)}
              >
                <div className="conversation-info">
                  {editingConversation === name ? (
                    <div className="rename-container">
                      <input
                        type="text"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        className="rename-input"
                      />
                      <div className="rename-buttons">
                        <button className="confirm-rename" onClick={handleRename}>✓</button>
                        <button className="cancel-rename" onClick={cancelRename}>✕</button>
                      </div>
                    </div>
                  ) : (
                    <div className="conversation-name">{name}</div>
                  )}
                  <div className="conversation-preview">
                    {convo.messages.length > 0 
                      ? convo.messages[convo.messages.length - 1].content.length > 25 
                        ? `${convo.messages[convo.messages.length - 1].content.slice(0, 25)}...`
                        : convo.messages[convo.messages.length - 1].content
                      : "新对话"}
                  </div>
                  <div className="conversation-time">{convo.time}</div>
                </div>
                
                <div className="conversation-actions">
                  <button 
                    className="rename-conversation" 
                    onClick={(e) => renameConversation(name, e)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L7 20.5l-4 1 1-4L18.5 2.5z"></path>
                    </svg>
                  </button>
                  <button 
                    className="delete-conversation" 
                    onClick={(e) => deleteConversation(name, e)}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"></polyline>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="no-conversations">
              还没有历史对话，快来开启新聊天吧！
            </div>
          )}
        </div>
        {/* 退出按钮：左下角，风格与 .age-option 一致，且不随 conversations-list 滚动 */}
        <div style={{ width: '100%', position: 'absolute', bottom: 0, left: 0, padding: '28px 0 16px 0', background: 'transparent', display: 'flex', justifyContent: 'center', pointerEvents: 'auto' }}>
          <button
            className="save-settings logout-btn"
            style={{ width: '80%', height: '48px', fontSize: '1.1rem', justifyContent: 'center', marginBottom: '0', lineHeight: '48px', padding: 0, textAlign: 'center', display: 'flex', alignItems: 'center' }}
            onClick={handleLogout}
          >
            退出登录
          </button>
        </div>
      </aside>
      
      {!showSidebar && (
        <button className="expand-sidebar" onClick={() => setShowSidebar(true)}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      )}
      
      {(appState === "initial" || appState === "expanded") && (
        <div 
          className="initial-screen" 
          ref={initialScreenRef}
          onClick={focusInput}
        >
          <div className="movie-art-content">
            <div className="glass-header">
              <h1>FILM&PILOT</h1>
              <p className="subtitle">I know what you want</p>
            </div>
            
            <div className="search-section">
              <div className="search-container">
                <input
                  ref={inputRef}
                  type="text"
                  className="search-input"
                  placeholder="探索电影艺术世界..."
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                />
                <button 
                  className="search-btn" 
                  onClick={handleSend}
                >
                  搜索
                </button>
              </div>
            </div>
            
            <RecommendationBar isExpanded={isRecommendationExpanded} />
          </div>
        </div>
      )}
      
      {appState === "chat" && (
        <main className={`chat-container ${!showSidebar ? 'expanded' : ''}`}>
          <header className="chat-header">
            <div className="header-title">
              <h1>FilmPilot</h1>
              <div className="title-divider"></div>
            </div>
            <div className="header-controls">
              <button 
                className="age-btn" 
                onClick={() => setShowAgeSettings(!showAgeSettings)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="8" r="5"></circle>
                  <path d="M8.21 13.89L7 23l5-3 5 3-1.21-9.12"></path>
                </svg>
              </button>
              
              <button 
                className="test-btn" 
                onClick={() => setShowTestSettings(!showTestSettings)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </button>
              
              <button 
                className="options-btn" 
                onClick={() => setShowOptions(!showOptions)}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
              </button>
            </div>
          </header>
          
          <div className="messages-container" ref={messagesRef}>
            <div className="messages">
              {currentMessages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role}`}>
                  <div className="message-content">
                    {msg.mapData ? (
                      <AmapRouteBox 
                        origin={msg.mapData.origin}
                        destination={msg.mapData.destination}
                        city={msg.mapData.city}
                        mode={msg.mapData.mode}
                        amapjs_key={msg.mapData.amapjs_key || "a64c3600e44f633e2af4fd8b0c8bb5eb"}
                        security_key={msg.mapData.security_key || "57a82ef7ebde5553411673bc0ae7c6b2"}
                      />
                    ) : (
                      msg.role === 'bot' ? formatBotMessage(msg.content) : <p>{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}
              
              {/* 思考中的动画 */}
              {isThinking && (
                <div className="message bot">
                  <div className="message-content">
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
              
              {/* 流式输出 */}
              {streamingBotMsg && (
                <div className="message bot">
                  <div className="message-content">
                    {formatBotMessage(streamingBotMsg, true)}
                    <div className="typing-indicator">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          </div>
          
          <div className="input-area bottom">
            <div className="input-container">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="探索对话世界..."
                className="message-input"
              />
              <button 
                className="send-button" 
                onClick={handleSend}
              >
                发送
              </button>
            </div>
          </div>
        </main>
      )}
      
      <aside className={`options-panel ${showOptions ? 'open' : ''}`}>
        <div className="options-header">
          <h3>主题设置</h3>
          <button className="close-options" onClick={() => setShowOptions(false)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="options-content">
          <div className="option-section">
            <h4>主题设置</h4>
            <div className="theme-options">
              <button 
                className={`theme-option ${theme === 'day' ? 'selected' : ''}`}
                onClick={() => changeTheme('day')}
              >
                <div className="theme-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="5"></circle>
                    <line x1="12" y1="1" x2="12" y2="3"></line>
                    <line x1="12" y1="21" x2="12" y2="23"></line>
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                    <line x1="1" y1="12" x2="3" y2="12"></line>
                    <line x1="21" y1="12" x2="23" y2="12"></line>
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                  </svg>
                </div>
                <span>日间模式</span>
              </button>
              <button 
                className={`theme-option ${theme === 'night' ? 'selected' : ''}`}
                onClick={() => changeTheme('night')}
              >
                <div className="theme-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                  </svg>
                </div>
                <span>夜间模式</span>
              </button>
              <button 
                className={`theme-option ${theme === 'eye' ? 'selected' : ''}`}
                onClick={() => changeTheme('eye')}
              >
                <div className="theme-icon">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M20.24 12.24a6 6 0 0 1-8.49 8.49L5 10.5V19h8.5z"></path>
                    <path d="M16 8a2 2 0 1 1-4 0 2 2 0 0 1 4 0z"></path>
                  </svg>
                </div>
                <span>护眼模式</span>
              </button>
            </div>
          </div>
          <button className="save-settings" onClick={() => setShowOptions(false)}>保存设置</button>
        </div>
      </aside>
      
      <aside className={`age-panel ${showAgeSettings ? 'open' : ''}`}>
        <div className="options-header">
          <h3>年龄与性别设置</h3>
          <button className="close-options" onClick={() => setShowAgeSettings(false)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="options-content">
          <div className="option-section">
            <h4>年龄范围</h4>
            <div className="age-options">
              {ageRanges.map(range => (
                <button
                  key={range}
                  className={`age-option ${selectedAgeRange === range ? 'selected' : ''}`}
                  onClick={() => setSelectedAgeRange(range)}
                >
                  <span>{range}</span>
                </button>
              ))}
            </div>
          </div>
          
          <div className="option-section">
            <h4>性别设置</h4>
            <div className="age-options">
              {genders.map(gender => (
                <button
                  key={gender}
                  className={`age-option ${selectedGender === gender ? 'selected' : ''}`}
                  onClick={() => setSelectedGender(gender)}
                >
                  <span>{gender}</span>
                </button>
              ))}
            </div>
          </div>
          
          <button className="save-settings" onClick={() => saveSettings('age')}>保存设置</button>
        </div>
      </aside>
      
      <aside className={`test-panel ${showTestSettings ? 'open' : ''}`}>
        <div className="options-header">
          <h3>偏好测试</h3>
          <button className="close-options" onClick={() => setShowTestSettings(false)}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        <div className="options-content">
          <div className="option-section">
            <h4>电影类型偏好</h4>
            <div className="preference-grid">
              {movieGenres.map(genre => (
                <button
                  key={genre}
                  className={`pref-option ${selectedMoviePreferences.includes(genre) ? 'selected' : ''}`}
                  onClick={() => {
                    setSelectedMoviePreferences(prev =>
                      prev.includes(genre)
                        ? prev.filter(g => g !== genre)
                        : [...prev, genre]
                    );
                  }}
                >
                  {genre}
                </button>
              ))}
            </div>
          </div>
          
          <button className="save-settings" onClick={() => saveSettings('test')}>完成测试</button>
        </div>
      </aside>
      
      {appState === "chat" && isRecommendationExpanded && (
        <div className="recommendation-bar-container">
          <RecommendationBar isExpanded={true} />
        </div>
      )}
      
      {appState === "chat" && !isRecommendationExpanded && (
        <button 
          className="show-recommendation-btn"
          onClick={toggleRecommendations}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="3" y1="9" x2="21" y2="9"></line>
            <line x1="9" y1="21" x2="9" y2="9"></line>
          </svg>
          <span>今日精选</span>
        </button>
      )}
    </div>
  );
}

export default App;
