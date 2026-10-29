from django import forms
from .models import ContactMessage, ProductReview, Product
from django.contrib.auth.models import User

class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "phone", "email", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Nguyễn Văn A"}),
            "phone": forms.TextInput(attrs={"placeholder": "090 xxx xx xx", "inputmode": "tel"}),
            "email": forms.EmailInput(attrs={"placeholder": "email@example.com"}),
            "message": forms.Textarea(attrs={"placeholder": "Bạn cần MINOO tư vấn điều gì?"}),
        }
        error_messages = {
            "name": {"required": "Vui lòng nhập họ tên."},
            "phone": {"required": "Vui lòng nhập số điện thoại."},
            "message": {"required": "Vui lòng nhập nội dung."},
            "email": {"invalid": "Email chưa đúng định dạng."},
        }

    def clean_phone(self):
        phone = self.cleaned_data["phone"].replace(" ", "").replace(".", "")
        if not phone.isdigit() or not (9 <= len(phone) <= 11):
            raise forms.ValidationError("Số điện thoại chưa đúng, vui lòng kiểm tra lại.")
        return phone


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ["reviewer_name", "rating", "comment"]
        widgets = {
            "reviewer_name": forms.TextInput(attrs={
                "placeholder": "Nhập tên của bạn",
                "class": "review-input",
                "maxlength": "100",
            }),
            "rating": forms.Select(attrs={
                "class": "review-input",
            }),
            "comment": forms.Textarea(attrs={
                "placeholder": "Chia sẻ trải nghiệm của bạn về sản phẩm...",
                "class": "review-input",
                "rows": 4,
                "maxlength": "2000",
            }),
        }

# =========================================================
# ADMIN - THÊM SẢN PHẨM TỪ ẢNH NHẬN DIỆN
# =========================================================

class AdminProductRecognitionCreateForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "sku",
            "name",
            "category",
            "frame_shape",
            "material",
            "color",
            "size",
            "gender",
            "original_price",
            "sale_price",
            "stock",
            "description",
            "is_active",
            "is_featured",
        ]

        widgets = {

            "sku": forms.TextInput(attrs={
                "placeholder": "Ví dụ: MN-001",
            }),

            "name": forms.TextInput(attrs={
                "placeholder": "Tên sản phẩm",
            }),

            "frame_shape": forms.TextInput(attrs={
                "placeholder": "Ví dụ: Tròn, Vuông, Mắt mèo...",
            }),

            "material": forms.TextInput(attrs={
                "placeholder": "Ví dụ: Acetate, TR90...",
            }),

            "color": forms.TextInput(attrs={
                "placeholder": "Ví dụ: Đen, Nâu...",
            }),

            "size": forms.TextInput(attrs={
                "placeholder": "Ví dụ: 52-18-140",
            }),

            "original_price": forms.NumberInput(attrs={
                "placeholder": "Giá niêm yết",
                "min": "0",
            }),

            "sale_price": forms.NumberInput(attrs={
                "placeholder": "Giá bán",
                "min": "0",
            }),

            "stock": forms.NumberInput(attrs={
                "placeholder": "Số lượng",
                "min": "0",
            }),

            "description": forms.Textarea(attrs={
                "placeholder": "Mô tả sản phẩm...",
                "rows": 5,
            }),

            "is_active": forms.CheckboxInput(),

            "is_featured": forms.CheckboxInput(),
        }


class RegisterForm(forms.Form):

    name = forms.CharField(
        max_length=150,
        label='Họ và tên'
    )

    email = forms.EmailField(
        label='Email'
    )

    phone = forms.CharField(
        max_length=20,
        label='Số điện thoại'
    )

    password1 = forms.CharField(
        label='Mật khẩu',
        widget=forms.PasswordInput
    )

    password2 = forms.CharField(
        label='Xác nhận mật khẩu',
        widget=forms.PasswordInput
    )


    def clean_email(self):

        email = self.cleaned_data[
            'email'
        ].strip().lower()

        if User.objects.filter(
            username=email
        ).exists():

            raise forms.ValidationError(
                'Email này đã được đăng ký.'
            )

        return email


    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get(
            'password1'
        )

        password2 = cleaned_data.get(
            'password2'
        )

        if (
            password1 and
            password2 and
            password1 != password2
        ):

            self.add_error(
                'password2',
                'Mật khẩu xác nhận không khớp.'
            )

        return cleaned_data