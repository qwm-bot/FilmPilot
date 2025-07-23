// API服务层 - 处理与后端的通信
const API_BASE_URL = 'http://localhost:5000'; // 根据实际后端地址调整

class ApiService {
  // 发送消息到后端
  static async sendMessage(message, conversationId, userProfile = {}) {
    try {
      const requestData = {
        currentInput: message,
        conversation_id: conversationId,
        ...userProfile
      };

      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API调用失败:', error);
      throw error;
    }
  }

  // 创建新的对话ID
  static generateConversationId() {
    return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // 获取对话历史（如果需要从后端获取）
  static async getConversationHistory(conversationId) {
    try {
      const response = await fetch(`${API_BASE_URL}/conversation/${conversationId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('获取对话历史失败:', error);
      return null;
    }
  }
}

export default ApiService; 