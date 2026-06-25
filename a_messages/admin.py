from django.contrib import admin
from .models import Conversation


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation_participants")
    
    def conversation_participants(self, obj):
        participants = obj.convuser_set.all()
        return ", ".join([p.user.username for p in participants])
    conversation_participants.short_description = "Participants"
    