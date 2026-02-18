# 📋 EventPredict — План доработок для соответствия Polymarket

## 🎯 Цель
Перенести функционал Polymarket в Telegram Mini App с полной функциональностью и похожим UI/UX.

---

## 1. 🔴 КРИТИЧНО: Исправление изображений в Telegram Mini App

### Проблема
Изображения не загружаются в Telegram Mini App, но работают на сайте.

### Причина
- Telegram WebApp имеет строгие ограничения на CORS
- Proxy endpoint может не работать корректно
- Возможно mixed content (HTTP/HTTPS)

### Решение

#### 1.1 Обновить proxy endpoint для Telegram
```python
@app.get("/proxy/image")
async def proxy_image(url: str, telegram_webapp: bool = False):
    """Прокси для изображений с поддержкой Telegram"""
    headers = {
        "User-Agent": "TelegramBot/1.0",  # Специальный UA для Telegram
        "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        "Access-Control-Allow-Origin": "*",  # CORS для Telegram
    }
    
    # Для Telegram возвращаем с правильными заголовками
    if telegram_webapp:
        headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        headers["Access-Control-Allow-Origin"] = "*"
```

#### 1.2 Base64 fallback для Telegram
```javascript
// В script.js
async function loadImageForTelegram(imageUrl) {
    try {
        // Пробуем через proxy
        const response = await fetch(`${backendUrl}/proxy/image?url=${encodeURIComponent(imageUrl)}&telegram_webapp=1`);
        
        if (!response.ok) {
            throw new Error('Proxy failed');
        }
        
        // Конвертируем в base64 для Telegram
        const blob = await response.blob();
        return await blobToBase64(blob);
    } catch (e) {
        // Fallback на placeholder
        return null;
    }
}
```

#### 1.3 Тесты
```python
def test_image_proxy_for_telegram():
    """Проверка что изображения работают в Telegram"""
    # 1. Проверка proxy endpoint
    response = requests.get(f"{BASE_URL}/proxy/image?url=TEST_URL&telegram_webapp=1")
    assert response.status_code == 200
    assert 'Access-Control-Allow-Origin' in response.headers
    
    # 2. Проверка CORS заголовков
    assert response.headers['Access-Control-Allow-Origin'] == '*'
    
    # 3. Проверка что изображение возвращается
    assert len(response.content) > 0
```

---

## 2. 🟡 Графики как на Polymarket

### Текущее состояние
- Несколько линий для каждого исхода
- Простой дизайн

### Цель
- **Одна линия** с градиентным заполнением
- Градиент от зелёного (сверху) к красному (снизу)
- Идентично Polymarket

### Решение

#### 2.1 Обновить renderEventChart()
```javascript
async function renderEventChart(eventId, options) {
    // ... загрузка данных ...
    
    // ТОЛЬКО ОДНА ЛИНИЯ для Yes/Up опции
    const primaryOption = options.find(opt => opt.text.toLowerCase() === 'yes' || opt.index === 0);
    
    const datasets = [{
        label: 'Price',
        data: priceData,
        borderColor: '#22c55e',  // Зелёная линия
        borderWidth: 2,
        fill: true,
        // Градиент для фона
        backgroundColor: (context) => {
            const ctx = context.chart.ctx;
            const gradient = ctx.createLinearGradient(0, 0, 0, 300);
            gradient.addColorStop(0, 'rgba(34, 197, 94, 0.3)');  // Зелёный сверху
            gradient.addColorStop(1, 'rgba(239, 68, 68, 0.1)');  // Красный снизу
            return gradient;
        },
        tension: 0.4,  // Более плавная кривая
        pointRadius: 0,
        pointHoverRadius: 5
    }];
    
    // Настройки графика как на Polymarket
    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },  // Скрыть легенду как на Polymarket
            tooltip: {
                mode: 'index',
                intersect: false,
                backgroundColor: 'rgba(15, 15, 18, 0.95)',
                titleColor: '#fff',
                bodyColor: '#a1a1aa',
                borderColor: 'rgba(255,255,255,0.1)',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: (context) => `Price: ${(context.raw * 100).toFixed(2)}%`
                }
            }
        },
        scales: {
            x: {
                display: true,
                grid: { display: false, drawBorder: false },
                ticks: { color: '#71717a', maxTicksLimit: 6 }
            },
            y: {
                display: true,
                min: 0,
                max: 1,
                grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false },
                ticks: {
                    color: '#71717a',
                    callback: (value) => `${(value * 100).toFixed(0)}%`
                }
            }
        },
        interaction: {
            intersect: false,
            mode: 'nearest'
        }
    };
}
```

#### 2.2 Тесты
```python
def test_chart_endpoint():
    """Проверка что данные для графика доступны"""
    event_id = get_test_event_id()
    response = requests.get(f"{BASE_URL}/events/{event_id}/price-history")
    assert response.status_code == 200
    
    data = response.json()
    assert isinstance(data, list)
    
    if len(data) > 0:
        # Проверка структуры
        point = data[0]
        assert 'price' in point
        assert 'timestamp' in point
        assert 'option_index' in point
        assert 0 <= point['price'] <= 1

def test_chart_gradient_in_frontend():
    """Проверка что график имеет градиент"""
    response = requests.get(f"{BASE_URL}/frontend/script.js")
    content = response.text
    
    # Проверка наличия градиента
    assert 'createLinearGradient' in content
    assert 'rgba(34, 197, 94' in content  # Зелёный
    assert 'rgba(239, 68, 68' in content  # Красный
```

---

## 3. 🟢 Комментарии к событиям

### Новая функциональность
- Раздел комментариев под каждым событием
- Возможность оставить комментарий
- Отображение комментариев от других пользователей

### Backend изменения

#### 3.1 Новая модель EventComment
```python
# api/models.py
class EventComment(Base):
    __tablename__ = "event_comments"
    
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id = Column(Integer, nullable=False)
    username = Column(String(255))
    comment_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    # Связи
    event = relationship("Event", back_populates="comments")
    user = relationship("User")
```

#### 3.2 API endpoints
```python
# api/index.py
class CommentRequest(BaseModel):
    telegram_id: int
    event_id: int
    comment_text: str

@app.get("/events/{event_id}/comments")
async def get_event_comments(event_id: int, db: Session = Depends(get_db)):
    """Получить комментарии к событию"""
    comments = db.query(EventComment).filter(
        EventComment.event_id == event_id,
        EventComment.is_deleted == False
    ).order_by(EventComment.created_at.desc()).limit(50).all()
    
    return {
        "comments": [
            {
                "id": c.id,
                "user_id": c.telegram_id,
                "username": c.username or f"User{c.telegram_id}",
                "comment_text": c.comment_text,
                "created_at": c.created_at.isoformat()
            }
            for c in comments
        ]
    }

@app.post("/events/{event_id}/comments")
async def add_event_comment(
    event_id: int,
    request: CommentRequest,
    db: Session = Depends(get_db)
):
    """Добавить комментарий к событию"""
    # Проверка пользователя
    user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверка события
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Создание комментария
    comment = EventComment(
        event_id=event_id,
        user_id=user.id,
        telegram_id=request.telegram_id,
        username=user.username,
        comment_text=request.comment_text[:1000]  # Лимит 1000 символов
    )
    db.add(comment)
    db.commit()
    
    return {
        "success": True,
        "comment": {
            "id": comment.id,
            "username": comment.username,
            "comment_text": comment.comment_text,
            "created_at": comment.created_at.isoformat()
        }
    }
```

#### 3.3 Frontend
```javascript
// В script.js - добавить секцию комментариев в модальное окно
function renderEventModal(event) {
    return `
        <div class="event-modal">
            <!-- Существующий контент -->
            ${renderEventChart(event.id, event.options)}
            
            <!-- Новая секция комментариев -->
            <div class="comments-section">
                <h3>Комментарии (${event.comments_count || 0})</h3>
                
                <div class="comments-list" id="comments-list-${event.id}">
                    <!-- Загрузка комментариев -->
                </div>
                
                <div class="comment-form">
                    <textarea 
                        id="comment-input-${event.id}"
                        placeholder="Оставить комментарий..."
                        maxlength="1000"
                        rows="3"
                    ></textarea>
                    <button onclick="postComment(${event.id})">
                        Отправить
                    </button>
                </div>
            </div>
        </div>
    `;
}

async function loadComments(eventId) {
    const response = await apiRequest(`/events/${eventId}/comments`);
    const commentsList = document.getElementById(`comments-list-${eventId}`);
    
    commentsList.innerHTML = response.comments.map(comment => `
        <div class="comment-item">
            <div class="comment-header">
                <span class="comment-author">${escapeHtml(comment.username)}</span>
                <span class="comment-time">${formatTime(comment.created_at)}</span>
            </div>
            <div class="comment-text">${escapeHtml(comment.comment_text)}</div>
        </div>
    `).join('');
}

async function postComment(eventId) {
    const input = document.getElementById(`comment-input-${eventId}`);
    const text = input.value.trim();
    
    if (!text) return;
    
    await apiRequest(`/events/${eventId}/comments`, {
        method: 'POST',
        body: JSON.stringify({
            telegram_id: getUserId(),
            event_id: eventId,
            comment_text: text
        })
    });
    
    input.value = '';
    loadComments(eventId);  // Обновить список
}
```

#### 3.4 Тесты
```python
def test_comments_api():
    """Проверка API комментариев"""
    # 1. Получить комментарии (пустой список)
    event_id = get_test_event_id()
    response = requests.get(f"{BASE_URL}/events/{event_id}/comments")
    assert response.status_code == 200
    assert 'comments' in response.json()
    
    # 2. Добавить комментарий
    comment_data = {
        "telegram_id": 123456789,
        "event_id": event_id,
        "comment_text": "Тестовый комментарий"
    }
    response = requests.post(
        f"{BASE_URL}/events/{event_id}/comments",
        json=comment_data
    )
    assert response.status_code == 200
    assert response.json()['success'] == True
    
    # 3. Проверить что комментарий появился
    response = requests.get(f"{BASE_URL}/events/{event_id}/comments")
    comments = response.json()['comments']
    assert len(comments) > 0
    assert comments[0]['comment_text'] == "Тестовый комментарий"
```

---

## 4. 🟢 Редактирование профиля (имя и аватар)

### Backend изменения

#### 4.1 Обновить модель User
```python
# api/models.py
class User(Base):
    # ... существующие поля ...
    custom_username = Column(String(255), nullable=True)  # Пользовательское имя
    avatar_url = Column(String(500), nullable=True)  # URL аватара
```

#### 4.2 API endpoints
```python
# api/index.py
class UpdateProfileRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    avatar_url: Optional[str] = None

@app.post("/user/profile/update")
async def update_profile(request: UpdateProfileRequest, db: Session = Depends(get_db)):
    """Обновить профиль пользователя"""
    user = db.query(User).filter(User.telegram_id == request.telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if request.username:
        user.custom_username = request.username[:50]
    
    if request.avatar_url:
        user.avatar_url = request.avatar_url[:500]
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "user": {
            "telegram_id": user.telegram_id,
            "username": user.custom_username or user.username,
            "avatar_url": user.avatar_url
        }
    }

@app.get("/user/{telegram_id}/profile")
async def get_user_profile(telegram_id: int, db: Session = Depends(get_db)):
    """Получить расширенный профиль"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "telegram_id": user.telegram_id,
        "username": user.custom_username or user.username,
        "original_username": user.username,
        "avatar_url": user.avatar_url,
        "balance_usdt": user.balance_usdt,
        "created_at": user.created_at.isoformat()
    }
```

#### 4.3 Frontend
```javascript
// В profile section добавить форму редактирования
function renderProfileSection() {
    return `
        <div class="profile-section">
            <div class="profile-header">
                <div class="profile-avatar" id="profile-avatar-display">
                    ${user.avatar_url 
                        ? `<img src="${user.avatar_url}" alt="Avatar">`
                        : `<div class="avatar-placeholder">${getUsername().charAt(0)}</div>`
                    }
                </div>
                
                <div class="profile-info">
                    <h2 id="profile-name-display">
                        ${user.custom_username || getUsername()}
                    </h2>
                    <p>ID: ${getUserId()}</p>
                </div>
                
                <button class="edit-profile-btn" onclick="showEditProfileModal()">
                    ✏️
                </button>
            </div>
            
            <!-- Modal для редактирования -->
            <div id="edit-profile-modal" class="modal" style="display:none">
                <div class="modal-content">
                    <h3>Редактировать профиль</h3>
                    
                    <div class="form-group">
                        <label>Имя пользователя</label>
                        <input 
                            type="text" 
                            id="edit-username-input"
                            value="${user.custom_username || getUsername()}"
                            maxlength="50"
                        />
                    </div>
                    
                    <div class="form-group">
                        <label>URL аватара</label>
                        <input 
                            type="url" 
                            id="edit-avatar-input"
                            value="${user.avatar_url || ''}"
                            placeholder="https://..."
                            maxlength="500"
                        />
                    </div>
                    
                    <div class="modal-actions">
                        <button onclick="hideEditProfileModal()">Отмена</button>
                        <button onclick="saveProfileChanges()" class="primary">Сохранить</button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

async function saveProfileChanges() {
    const username = document.getElementById('edit-username-input').value.trim();
    const avatarUrl = document.getElementById('edit-avatar-input').value.trim();
    
    const response = await apiRequest('/user/profile/update', {
        method: 'POST',
        body: JSON.stringify({
            telegram_id: getUserId(),
            username: username || null,
            avatar_url: avatarUrl || null
        })
    });
    
    if (response.success) {
        // Обновить UI
        location.reload();  // Или точечное обновление
    }
}
```

#### 4.4 Тесты
```python
def test_profile_update():
    """Проверка обновления профиля"""
    telegram_id = 123456789
    
    # 1. Обновить профиль
    update_data = {
        "telegram_id": telegram_id,
        "username": "CustomName",
        "avatar_url": "https://example.com/avatar.jpg"
    }
    response = requests.post(
        f"{BASE_URL}/user/profile/update",
        json=update_data
    )
    assert response.status_code == 200
    assert response.json()['success'] == True
    
    # 2. Проверить что данные обновились
    response = requests.get(f"{BASE_URL}/user/{telegram_id}/profile")
    profile = response.json()
    assert profile['username'] == "CustomName"
    assert profile['avatar_url'] == "https://example.com/avatar.jpg"
```

---

## 5. 🟢 Дополнительные улучшения для Polymarket-like UX

### 5.1 Быстрые ставки (Quick Bet)
```javascript
// Добавить кнопки быстрых ставок
function createQuickBetButtons() {
    return `
        <div class="quick-bet-buttons">
            <button onclick="quickBet(10)">$10</button>
            <button onclick="quickBet(50)">$50</button>
            <button onclick="quickBet(100)">$100</button>
            <button onclick="quickBet('max')">MAX</button>
        </div>
    `;
}
```

### 5.2 Портфолио пользователя
```python
@app.get("/user/{telegram_id}/portfolio")
async def get_user_portfolio(telegram_id: int, db: Session = Depends(get_db)):
    """Получить портфолио пользователя (активные позиции)"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    positions = db.query(UserPrediction).join(Event).filter(
        UserPrediction.user_id == user.id,
        UserPrediction.is_winner == None  # Активные позиции
    ).all()
    
    return {
        "positions": [
            {
                "event_id": p.event.id,
                "event_title": p.event.title,
                "option": p.event.options[p.option_index],
                "amount": p.amount,
                "current_value": calculate_current_value(p),
                "pnl": calculate_pnl(p)
            }
            for p in positions
        ]
    }
```

### 5.3 Уведомления о результатах
```python
# В scheduled tasks
def notify_winners():
    """Отправить уведомления победителям"""
    resolved_events = db.query(Event).filter(
        Event.is_resolved == True,
        Event.notified == False
    ).all()
    
    for event in resolved_events:
        winners = db.query(UserPrediction).filter(
            UserPrediction.event_id == event.id,
            UserPrediction.is_winner == True
        ).all()
        
        for winner in winners:
            # Отправить уведомление через Telegram Bot API
            send_telegram_notification(winner.telegram_id, ...)
        
        event.notified = True
```

---

## 6. 📊 Сводная таблица тестов

| Компонент | Тест | Статус |
|-----------|------|--------|
| Изображения | `test_image_proxy_for_telegram()` | 🔴 |
| Графики | `test_chart_endpoint()` | 🟡 |
| Графики | `test_chart_gradient_in_frontend()` | 🟡 |
| Комментарии | `test_comments_api()` | 🟢 |
| Профиль | `test_profile_update()` | 🟢 |
| Портфолио | `test_portfolio_endpoint()` | 🟢 |

---

## 7. 🚀 Приоритеты реализации

### P0 (Критично)
1. ✅ Исправить изображения для Telegram
2. ✅ Обновить графики (одна линия с градиентом)

### P1 (Важно)
3. ✅ Комментарии к событиям
4. ✅ Редактирование профиля

### P2 (Дополнительно)
5. Портфолио пользователя
6. Быстрые ставки
7. Уведомления

---

## 8. 📁 Структура новых файлов

```
tgqweasd/
├── api/
│   ├── models.py          # + EventComment модель
│   └── index.py           # + endpoints для комментариев и профиля
├── frontend/
│   ├── script.js          # + функции для комментариев, профиля, графиков
│   └── styles.css         # + стили для комментариев и форм
├── tests/
│   ├── test_images.py     # Тесты изображений
│   ├── test_charts.py     # Тесты графиков
│   ├── test_comments.py   # Тесты комментариев
│   └── test_profile.py    # Тесты профиля
└── TELEGRAM_FIXES.md      # Этот документ
```

---

## 9. ✅ Чеклист перед деплоем

- [ ] Изображения работают в Telegram Mini App
- [ ] Графики с одной линией и градиентом
- [ ] Комментарии добавляются и отображаются
- [ ] Профиль редактируется (имя + аватар)
- [ ] Все тесты проходят
- [ ] Логи чистые (нет ошибок CORS)

---

**Следующий шаг:** Начать с P0 — исправить изображения и графики.
