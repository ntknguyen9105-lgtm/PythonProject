document.addEventListener("DOMContentLoaded", function () {

    const categoryField = document.getElementById("id_category");

    if (!categoryField) {
        return;
    }


    /*
     * =====================================================
     * XÁC ĐỊNH CÁC TRƯỜNG
     * =====================================================
     */

    const frameFields = [
        "frame_shape",
        "material",
        "color",
        "size"
    ];

    const lensFields = [
        "lens_type",
        "lens_index",
        "lens_feature",
        "lens_diameter"
    ];


    /*
     * =====================================================
     * LẤY DÒNG FORM CỦA DJANGO ADMIN
     * =====================================================
     */

    function getFieldRow(fieldName) {

        const field = document.getElementById(
            "id_" + fieldName
        );

        if (!field) {
            return null;
        }

        return field.closest(".form-row");
    }


    /*
     * =====================================================
     * ẨN / HIỆN MỘT TRƯỜNG
     * =====================================================
     */

    function showField(fieldName, show) {

        const row = getFieldRow(fieldName);

        if (!row) {
            return;
        }

        row.style.display = show ? "" : "none";
    }


    /*
     * =====================================================
     * XÁC ĐỊNH DANH MỤC
     * =====================================================
     */

    function getCategoryName() {

        const selectedOption =
            categoryField.options[
                categoryField.selectedIndex
            ];

        if (!selectedOption) {
            return "";
        }

        return selectedOption.text
            .trim()
            .toLowerCase();
    }


    /*
     * =====================================================
     * CẬP NHẬT FORM
     * =====================================================
     */

    function updateProductFields() {

        const categoryName = getCategoryName();

        const isFrame =
            categoryName.includes("gọng kính") ||
            categoryName.includes("gong kinh");

        const isLens =
            categoryName.includes("tròng kính") ||
            categoryName.includes("trong kinh");


        /*
         * GỌNG KÍNH
         */

        frameFields.forEach(function (fieldName) {

            showField(
                fieldName,
                isFrame
            );

        });


        /*
         * TRÒNG KÍNH
         */

        lensFields.forEach(function (fieldName) {

            showField(
                fieldName,
                isLens
            );

        });


        /*
         * Nếu chưa chọn danh mục
         * thì ẩn cả hai nhóm
         */

        if (!isFrame && !isLens) {

            frameFields.forEach(function (fieldName) {

                showField(
                    fieldName,
                    false
                );

            });

            lensFields.forEach(function (fieldName) {

                showField(
                    fieldName,
                    false
                );

            });

        }

    }


    /*
     * =====================================================
     * KHI THAY ĐỔI DANH MỤC
     * =====================================================
     */

    categoryField.addEventListener(
        "change",
        updateProductFields
    );


    /*
     * =====================================================
     * CHẠY NGAY KHI MỞ TRANG
     * =====================================================
     */

    updateProductFields();

});