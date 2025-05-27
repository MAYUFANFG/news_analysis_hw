import torch
import os
import torch.nn.functional as F
from torch import nn

class QwenForClassifier(nn.Module):
    def __init__(self, base_model, hidden_size, num_labels):
        super(QwenForClassifier, self).__init__()
        # 凍結 base model 的參數
        self.base_model = base_model
        
        for param in self.base_model.parameters():
            param.requires_grad = False
            
        # 注意力池化機制
        self.attention_pooler = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.Tanh(),
            nn.Linear(128, 1)
        )
        
        # 多層融合權重 (最後4層)
        self.layer_weights = nn.Parameter(torch.ones(4) / 4)
        
        # 增強型分類器
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.2),
            
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.1),
            
            nn.Linear(128, num_labels)
        )
        
        # 保存配置
        self.config = base_model.config
        self.config.num_labels = num_labels
    
    def forward(self, input_ids, attention_mask=None, labels=None):
        # 獲取所有隱藏層狀態
        outputs = self.base_model(
            input_ids=input_ids, 
            attention_mask=attention_mask,
            output_hidden_states=True
        )
        
        # 獲取最後4層隱藏狀態
        hidden_states = outputs.hidden_states
        if hidden_states is None:
            # 如果模型沒有返回hidden_states，使用last_hidden_state
            last_hidden = outputs.last_hidden_state
            sequence_output = last_hidden
        else:
            # 融合最後4層 (或可用層數)
            last_layers = hidden_states[-4:] if len(hidden_states) >= 4 else hidden_states[1:]
            layer_weights = F.softmax(self.layer_weights[:len(last_layers)], dim=0)
            
            # 加權融合多層特徵
            sequence_output = torch.zeros_like(last_layers[0])
            for i, layer in enumerate(last_layers):
                sequence_output += layer_weights[i].unsqueeze(-1).unsqueeze(-1) * layer
        
        # 注意力池化
        attention_scores = self.attention_pooler(sequence_output)
        attention_probs = F.softmax(attention_scores, dim=1)
        context_vector = torch.matmul(attention_probs.transpose(-1, -2), sequence_output).squeeze(1)
        
        # 也計算平均池化向量
        mean_pooled = torch.mean(sequence_output, dim=1)
        
        # 結合注意力池化和平均池化 (殘差連接)
        combined_repr = context_vector + mean_pooled
            
        # 分類預測
        logits = self.classifier(combined_repr)
        
        # 計算損失
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits, labels)
            
        return {"loss": loss, "logits": logits}
    
    def save_model(self, output_dir=None):
        """保存分類器權重和配置"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存分類器權重
        classifier_path = os.path.join(output_dir, "classifier_weights.pt")
        model_dict = {
            'classifier': self.classifier.state_dict(),
            'attention_pooler': self.attention_pooler.state_dict(),
            'layer_weights': self.layer_weights,
            'config': {
                'num_labels': self.config.num_labels,
                'hidden_size': self.config.hidden_size
            }
        }
        torch.save(model_dict, classifier_path)
        print(f"已保存分類器權重至 {classifier_path}")
    
    def load_model(self, model_dir, device=None):
        """載入分類器權重"""
        if device is None:
            device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            
        classifier_path = os.path.join(model_dir, "classifier_weights.pt")
        if os.path.exists(classifier_path):
            model_dict = torch.load(classifier_path, map_location=device, weights_only=True)
            
            # 載入各組件
            self.classifier.load_state_dict(model_dict['classifier'])
            self.attention_pooler.load_state_dict(model_dict['attention_pooler'])
            self.layer_weights.data = model_dict['layer_weights'].to(device)
            
            print(f"已載入分類器權重: {classifier_path}")
            return True
        else:
            print(f"警告: 找不到分類器權重檔案 {classifier_path}")
            return False