from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
import logging
from .models import User, UserPassion, UserPassionSelection, PersonalityTestResult, UserInterests

# Créer un logger pour cette app
logger = logging.getLogger('users')


class UserPassionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPassion
        fields = ['id', 'name', 'category', 'description', 'icon']


class UserPassionSelectionSerializer(serializers.ModelSerializer):
    passion = UserPassionSerializer(read_only=True)
    passion_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserPassionSelection
        fields = ['id', 'passion', 'passion_id', 'intensity_level', 'selected_at']
        read_only_fields = ['selected_at']


class PersonalityTestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalityTestResult
        fields = [
            'extraversion_score', 'intuition_score', 'thinking_score', 'judging_score',
            'dominance_score', 'influence_score', 'steadiness_score', 'conscientiousness_score',
            'mbti_result', 'disc_result', 'test_duration_seconds', 'completed_at'
        ]
        read_only_fields = ['completed_at']


class UserSerializer(serializers.ModelSerializer):
    passion_selections = UserPassionSelectionSerializer(many=True, read_only=True)
    personality_result = PersonalityTestResultSerializer(read_only=True)
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    is_premium_active = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'username',
            'phone', 'birth_date', 'age', 'gender', 'profile_picture', 'bio', 'location',
            'personality_type', 'disc_type', 'personality_test_completed', 'personality_test_date',
            'email_verified', 'onboarding_completed', 'is_premium', 'is_premium_active', 'premium_until',
            'passion_selections', 'personality_result', 'created_at', 'last_login_at'
        ]
        read_only_fields = [
            'id', 'email_verified', 'personality_test_completed', 'personality_test_date',
            'is_premium', 'premium_until', 'created_at', 'last_login_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour du profil utilisateur"""
    passion_selections = UserPassionSelectionSerializer(many=True, read_only=True)
    personality_result = PersonalityTestResultSerializer(read_only=True)
    age = serializers.ReadOnlyField()
    full_name = serializers.ReadOnlyField()
    is_premium_active = serializers.ReadOnlyField()
    interests = serializers.SerializerMethodField()
    
    def get_interests(self, obj):
        """Récupérer les intérêts de l'utilisateur depuis UserInterests"""
        try:
            user_interests = UserInterests.objects.get(user=obj)
            return user_interests.selected_interests
        except UserInterests.DoesNotExist:
            return []
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'birth_date', 'age', 'gender', 'profile_picture', 'bio', 'location',
            'personality_type', 'disc_type', 'personality_test_completed',
            'onboarding_completed', 'is_premium_active', 'premium_until',
            'passion_selections', 'personality_result', 'interests'
        ]
        read_only_fields = [
            'id', 'email', 'personality_type', 'disc_type', 'personality_test_completed',
            'is_premium_active', 'premium_until'
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm']
    
    def validate(self, attrs):
        logger.debug(f"Validation des données d'inscription: {attrs}")
        if attrs['password'] != attrs['password_confirm']:
            logger.warning("Les mots de passe ne correspondent pas")
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        return attrs
    
    def create(self, validated_data):
        logger.debug(f"Création d'utilisateur avec: {validated_data}")
        validated_data.pop('password_confirm')
        try:
            user = User.objects.create_user(
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=validated_data['password'],
                username=validated_data['email']  # Use email as username
            )
            logger.info(f"Utilisateur créé avec succès dans le serializer: {user.email}")
            return user
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur dans le serializer: {str(e)}", exc_info=True)
            raise serializers.ValidationError(f"Erreur lors de la création de l'utilisateur: {str(e)}")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(request=self.context.get('request'),
                              username=email, password=password)
            if not user:
                raise serializers.ValidationError('Email ou mot de passe incorrect.')
            if not user.is_active:
                raise serializers.ValidationError('Ce compte est désactivé.')
        else:
            raise serializers.ValidationError('Email et mot de passe requis.')
        
        attrs['user'] = user
        return attrs


class PersonalityTestSubmissionSerializer(serializers.Serializer):
    """Serializer pour soummettre les résultats du test de personnalité"""
    # Réponses aux questions (liste de scores ou réponses)
    extraversion_score = serializers.IntegerField(min_value=0, max_value=100)
    intuition_score = serializers.IntegerField(min_value=0, max_value=100)
    thinking_score = serializers.IntegerField(min_value=0, max_value=100)
    judging_score = serializers.IntegerField(min_value=0, max_value=100)
    
    dominance_score = serializers.IntegerField(min_value=0, max_value=100)
    influence_score = serializers.IntegerField(min_value=0, max_value=100)
    steadiness_score = serializers.IntegerField(min_value=0, max_value=100)
    conscientiousness_score = serializers.IntegerField(min_value=0, max_value=100)
    
    test_duration_seconds = serializers.IntegerField(min_value=0)
    
    def calculate_personality_types(self, validated_data):
        """Calculer les types MBTI et DISC basés sur les scores"""
        # MBTI calculation
        mbti = ""
        mbti += "E" if validated_data['extraversion_score'] >= 50 else "I"
        mbti += "N" if validated_data['intuition_score'] >= 50 else "S"
        mbti += "T" if validated_data['thinking_score'] >= 50 else "F"
        mbti += "J" if validated_data['judging_score'] >= 50 else "P"
        
        # DISC calculation (dominant type)
        disc_scores = {
            'D': validated_data['dominance_score'],
            'I': validated_data['influence_score'],
            'S': validated_data['steadiness_score'],
            'C': validated_data['conscientiousness_score']
        }
        disc_result = max(disc_scores, key=disc_scores.get)
        
        return mbti, disc_result


class PassionSelectionSerializer(serializers.Serializer):
    """Serializer pour la sélection des passions"""
    passion_selections = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        ),
        min_length=1,
        max_length=10
    )
    
    def validate_passion_selections(self, value):
        """Valider que les passions existent"""
        for selection in value:
            if 'passion_id' not in selection or 'intensity_level' not in selection:
                raise serializers.ValidationError(
                    "Chaque sélection doit contenir passion_id et intensity_level"
                )
            
            try:
                passion_id = int(selection['passion_id'])
                intensity_level = int(selection['intensity_level'])
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "passion_id et intensity_level doivent être des entiers"
                )
            
            if not UserPassion.objects.filter(id=passion_id, is_active=True).exists():
                raise serializers.ValidationError(f"Passion avec l'ID {passion_id} n'existe pas")
            
            if not 1 <= intensity_level <= 5:
                raise serializers.ValidationError("intensity_level doit être entre 1 et 5")
        
        return value


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cette adresse email.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    confirm_password = serializers.CharField()
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Les mots de passe ne correspondent pas.")
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer pour la vérification d'email"""
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        from .models import User, VerificationCode
        
        email = attrs.get('email')
        code = attrs.get('code')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Utilisateur non trouvé.")
        
        # Vérifier le code
        verification_code = VerificationCode.objects.filter(
            user=user,
            code=code,
            code_type='EMAIL_VERIFICATION',
            is_used=False
        ).first()
        
        if not verification_code:
            raise serializers.ValidationError("Code de vérification invalide.")
        
        if verification_code.is_expired:
            raise serializers.ValidationError("Code de vérification expiré.")
        
        attrs['user'] = user
        attrs['verification_code'] = verification_code
        return attrs 