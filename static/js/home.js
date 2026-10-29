document.addEventListener(
   "DOMContentLoaded",
   function () {




       /* =================================================
          01. HERO SLIDER
       ================================================= */


       const heroSlides =
           document.querySelectorAll(
               ".hero-slide"
           );




       const heroDots =
           document.querySelectorAll(
               ".hero-dot"
           );




       const heroNumber =
           document.getElementById(
               "currentHeroNumber"
           );




       let currentHero = 0;


       let heroTimer;




       function showHeroSlide(
           index
       ) {


           currentHero = index;




           heroSlides.forEach(
               function (
                   slide,
                   slideIndex
               ) {


                   slide.classList.toggle(
                       "active",
                       slideIndex === index
                   );


               }
           );




           heroDots.forEach(
               function (
                   dot,
                   dotIndex
               ) {


                   dot.classList.toggle(
                       "active",
                       dotIndex === index
                   );


               }
           );




           if (
               heroNumber
           ) {


               heroNumber.textContent =
                   String(
                       index + 1
                   )
                   .padStart(
                       2,
                       "0"
                   );


           }


       }






       function startHeroSlider() {


           clearInterval(
               heroTimer
           );




           heroTimer =
               setInterval(
                   function () {


                       currentHero++;


                       if (
                           currentHero >=
                           heroSlides.length
                       ) {


                           currentHero = 0;


                       }


                       showHeroSlide(
                           currentHero
                       );


                   },
                   5200
               );


       }






       heroDots.forEach(
           function (
               dot,
               index
           ) {


               dot.addEventListener(
                   "click",
                   function () {


                       showHeroSlide(
                           index
                       );


                       startHeroSlider();


                   }
               );


           }
       );




       if (
           heroSlides.length
       ) {


           showHeroSlide(0);


           startHeroSlider();


       }






       /* =================================================
          02. REVEAL ON SCROLL
       ================================================= */


       const revealItems =
           document.querySelectorAll(
               ".reveal"
           );




       if (
           "IntersectionObserver"
           in
           window
       ) {


           const revealObserver =
               new IntersectionObserver(


                   function (
                       entries,
                       observer
                   ) {


                       entries.forEach(
                           function (
                               entry
                           ) {


                               if (
                                   entry
                                   .isIntersecting
                               ) {


                                   entry
                                       .target
                                       .classList
                                       .add(
                                           "visible"
                                       );




                                   observer
                                       .unobserve(
                                           entry
                                               .target
                                       );


                               }


                           }
                       );


                   },


                   {


                       threshold: .12,


                       rootMargin:
                           "0px 0px -40px 0px"


                   }


               );




           revealItems.forEach(
               function (
                   item,
                   index
               ) {


                   item.style
                       .transitionDelay =
                           (
                               index % 4
                           )
                           *
                           65
                           +
                           "ms";




                   revealObserver
                       .observe(
                           item
                       );


               }
           );


       }


       else {


           revealItems.forEach(
               function (
                   item
               ) {


                   item
                       .classList
                       .add(
                           "visible"
                       );


               }
           );


       }






       /* =================================================
          03. SCROLL PROGRESS
       ================================================= */


       const progress =
           document.getElementById(
               "homeProgress"
           );




       function updateProgress() {


           if (
               !progress
           ) {


               return;


           }




           const scrollTop =
               window.scrollY
               ||
               document
                   .documentElement
                   .scrollTop;




           const pageHeight =
               document
                   .documentElement
                   .scrollHeight
               -
               window
                   .innerHeight;




           let percentage = 0;




           if (
               pageHeight > 0
           ) {


               percentage =
                   (
                       scrollTop
                       /
                       pageHeight
                   )
                   *
                   100;


           }




           progress.style
               .width =
                   percentage
                   +
                   "%";


       }




       window
           .addEventListener(
               "scroll",
               updateProgress,
               {
                   passive: true
               }
           );




       updateProgress();






       /* =================================================
          04. STORE SLIDER DRAG
       ================================================= */


       const storeSlider =
           document.getElementById(
               "storeSlider"
           );




       if (
           storeSlider
       ) {


           let isDown = false;


           let startX;


           let startScroll;






           storeSlider
               .addEventListener(
                   "mousedown",
                   function (
                       event
                   ) {


                       isDown = true;


                       storeSlider
                           .classList
                           .add(
                               "dragging"
                           );




                       startX =
                           event.pageX;




                       startScroll =
                           storeSlider
                               .scrollLeft;


                   }
               );






           window
               .addEventListener(
                   "mouseup",
                   function () {


                       isDown =
                           false;


                       storeSlider
                           .classList
                           .remove(
                               "dragging"
                           );


                   }
               );






           storeSlider
               .addEventListener(
                   "mousemove",
                   function (
                       event
                   ) {


                       if (
                           !isDown
                       ) {


                           return;


                       }




                       event
                           .preventDefault();




                       const distance =
                           (
                               event.pageX
                               -
                               startX
                           )
                           *
                           1.2;




                       storeSlider
                           .scrollLeft =
                               startScroll
                               -
                               distance;


                   }
               );


       }






       /* =================================================
          05. HERO PARALLAX
       ================================================= */


       const hero =
           document.querySelector(
               ".minoo-hero"
           );




       const allowMotion =
           window
               .matchMedia(
                   "(prefers-reduced-motion: no-preference)"
               )
               .matches;




       if (
           hero
           &&
           allowMotion
           &&
           window.innerWidth > 900
       ) {


           hero.addEventListener(
               "mousemove",
               function (
                   event
               ) {


                   const rect =
                       hero
                           .getBoundingClientRect();




                   const x =
                       (
                           event.clientX
                           -
                           rect.left
                       )
                       /
                       rect.width
                       -
                       .5;




                   const y =
                       (
                           event.clientY
                           -
                           rect.top
                       )
                       /
                       rect.height
                       -
                       .5;




                   const activeImage =
                       hero
                           .querySelector(
                               ".hero-slide.active img"
                           );




                   if (
                       activeImage
                   ) {


                       activeImage
                           .style
                           .transform =
                               "scale(1.018) translate("
                               +
                               (
                                   x
                                   *
                                   -8
                               )
                               +
                               "px,"
                               +
                               (
                                   y
                                   *
                                   -6
                               )
                               +
                               "px)";


                   }


               }
           );






           hero.addEventListener(
               "mouseleave",
               function () {


                   hero
                       .querySelectorAll(
                           ".hero-slide img"
                       )
                       .forEach(
                           function (
                               image
                           ) {


                               image.style
                                   .transform =
                                       "";


                           }
                       );


               }
           );


       }


   }
);


