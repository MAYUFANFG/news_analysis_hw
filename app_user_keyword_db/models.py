from django.db import models

# Create your models here.
class NewsData(models.Model):
    item_id = models.CharField(max_length=255, primary_key=True)
    date = models.DateField()
    category = models.CharField(max_length=255)
    title = models.TextField()
    content = models.TextField()
    sentiment = models.FloatField(null=True, blank=True)
    # summary = models.TextField(null=True, blank=True)
    top_key_freq = models.TextField(null=True, blank=True)  # Storing as string representation
    tokens = models.TextField(null=True, blank=True)
    tokens_v2 = models.TextField(null=True, blank=True)
    entities = models.TextField(null=True, blank=True)
    token_pos = models.TextField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)
    photo_link = models.URLField(null=True, blank=True)
    
    class Meta:
        db_table = 'news_data'
        
    def __str__(self):
        return f"{self.date}: {self.title}"
